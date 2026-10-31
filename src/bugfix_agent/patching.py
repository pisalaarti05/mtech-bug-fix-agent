"""Extract and apply unified diffs inside the disposable checkout."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path

def extract_diff(response: str) -> str:
    fence = chr(96) * 3
    fenced = re.search(re.escape(fence) + r"(?:diff|patch)?\s*\n(.*?)" + re.escape(fence), response.strip(), flags=re.DOTALL | re.IGNORECASE)
    text = fenced.group(1).strip() if fenced else response.strip()
    start = text.find("diff --git ")
    if start < 0:
        start = text.find("--- ")
    if start < 0:
        raise ValueError("The model response did not contain a unified diff.")
    diff = text[start:].strip() + "\n"
    if "+++ " not in diff or "@@" not in diff:
        raise ValueError("The response looks like an incomplete unified diff.")
    return diff

def apply_diff(repository: Path, diff: str) -> None:
    """Check then apply a diff; reject paths that could escape the checkout."""
    for line in diff.splitlines():
        if line.startswith(("+++ ", "--- ")):
            target = line[4:].split("\t", 1)[0]
            if target == "/dev/null":
                continue
            normalized = target.removeprefix("a/").removeprefix("b/")
            if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
                raise ValueError(f"Patch contains a path outside the checkout: {target}")
    patch_file = repository / ".bugfix-agent.patch"
    patch_file.write_text(diff, encoding="utf-8")
    try:
        check = subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=repository, capture_output=True, text=True, timeout=30)
        if check.returncode:
            raise RuntimeError(f"Patch validation failed: {(check.stderr or check.stdout).strip()}")
        applied = subprocess.run(["git", "apply", str(patch_file)], cwd=repository, capture_output=True, text=True, timeout=30)
        if applied.returncode:
            raise RuntimeError(f"Patch application failed: {(applied.stderr or applied.stdout).strip()}")
    finally:
        patch_file.unlink(missing_ok=True)
