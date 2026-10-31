"""Disposable repository checkout helpers."""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

class RepositoryCheckout:
    def __init__(self, url: str, commit: str | None = None):
        self.url = url
        self.commit = commit
        self._temporary = tempfile.TemporaryDirectory(prefix="bugfix-agent-")
        self.path = Path(self._temporary.name) / "repository"
        result = subprocess.run(["git", "clone", "--quiet", "--depth", "1", url, str(self.path)], capture_output=True, text=True, timeout=180)
        if result.returncode:
            self.close()
            raise RuntimeError(f"Could not clone repository: {(result.stderr or result.stdout).strip()}")
        if commit:
            fetch = subprocess.run(["git", "fetch", "--quiet", "--depth", "1", "origin", commit], cwd=self.path, capture_output=True, text=True, timeout=120)
            if fetch.returncode:
                self.close()
                raise RuntimeError(f"Could not fetch requested commit: {(fetch.stderr or fetch.stdout).strip()}")
            checkout = subprocess.run(["git", "checkout", "--quiet", "FETCH_HEAD"], cwd=self.path, capture_output=True, text=True, timeout=30)
            if checkout.returncode:
                self.close()
                raise RuntimeError(f"Could not check out requested commit: {(checkout.stderr or checkout.stdout).strip()}")
        self.resolved_commit = self._git("rev-parse", "HEAD")

    def _git(self, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=self.path, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    def close(self) -> None:
        self._temporary.cleanup()

    def __enter__(self) -> "RepositoryCheckout":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
