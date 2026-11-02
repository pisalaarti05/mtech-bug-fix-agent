"""End-to-end single repair attempt with an auditable JSON run record."""
from __future__ import annotations
import json
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from .issue import Issue
from .model import HuggingFaceModel
from .patching import apply_diff, extract_diff
from .prompts import repair_prompt
from .repository import RepositoryCheckout
from .retrieval import collect_chunks, retrieve

def run_repair(repository_url: str, issue: Issue, model_id: str, output_dir: Path, *, commit: str | None = None, use_retrieval: bool = True, top_k: int = 6, test_command: str | None = None, test_timeout: int = 600) -> Path:
    """Run a repair in a disposable clone and save its evidence record."""
    started = time.perf_counter()
    model = HuggingFaceModel(model_id)
    record: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_url": repository_url,
        "requested_commit": commit,
        "issue": {"title": issue.title, "body": issue.body, "source": issue.source},
        "model_id": model_id,
        "model_load_seconds": model.load_seconds,
        "condition": "retrieval" if use_retrieval else "no_retrieval",
        "top_k": top_k if use_retrieval else 0,
        "test_command": test_command,
    }
    with RepositoryCheckout(repository_url, commit) as checkout:
        record["resolved_commit"] = checkout.resolved_commit
        ranked = retrieve(issue.prompt_text, collect_chunks(checkout.path), limit=top_k) if use_retrieval else []
        context = [chunk for chunk, _ in ranked]
        record["retrieved_chunks"] = [
            {"path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line, "score": score, "text": chunk.text}
            for chunk, score in ranked
        ]
        prompt = repair_prompt(issue, context)
        record["prompt"] = prompt
        response = model.generate(prompt)
        record["generation_usage"] = model.last_usage
        record["model_response"] = response
        try:
            diff = extract_diff(response)
            apply_diff(checkout.path, diff)
            record["patch_valid"] = True
            record["patch"] = diff
        except (ValueError, RuntimeError) as exc:
            record["patch_valid"] = False
            record["patch_error"] = str(exc)
            record["test_status"] = "not_run"
        else:
            if test_command:
                command = shlex.split(test_command)
                if not command:
                    raise ValueError("The test command cannot be empty.")
                try:
                    result = subprocess.run(command, cwd=checkout.path, capture_output=True, text=True, timeout=test_timeout)
                    record["test_status"] = "passed" if result.returncode == 0 else "failed"
                    record["test_exit_code"] = result.returncode
                    record["test_stdout"] = result.stdout[-12000:]
                    record["test_stderr"] = result.stderr[-12000:]
                except subprocess.TimeoutExpired as exc:
                    record["test_status"] = "timeout"
                    record["test_stdout"] = (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else ""
                    record["test_stderr"] = (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else ""
            else:
                record["test_status"] = "not_run"
        record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{run_id}.json"
    output_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
