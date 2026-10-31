"""Issue text loading from a local description or a public GitHub issue."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

@dataclass(frozen=True)
class Issue:
    title: str
    body: str
    source: str
    @property
    def prompt_text(self) -> str:
        return f"{self.title.strip()}\n\n{self.body.strip()}".strip()

def load_issue(value: str) -> Issue:
    """Load issue text, fetching only public GitHub issue URLs."""
    if not value.startswith(("https://github.com/", "http://github.com/")):
        return Issue(title="Bug report", body=value, source="inline-text")
    parts = value.rstrip("/").split("/")
    if len(parts) < 7 or parts[5] != "issues" or not parts[6].isdigit():
        raise ValueError("Expected a GitHub issue URL like https://github.com/OWNER/REPO/issues/123")
    api_url = f"https://api.github.com/repos/{parts[3]}/{parts[4]}/issues/{parts[6]}"
    request = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github+json", "User-Agent": "repository-bugfix-agent"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not load public GitHub issue: {exc}") from exc
    if "pull_request" in payload:
        raise ValueError("The URL points to a pull request, not an issue.")
    return Issue(title=payload.get("title") or "Bug report", body=payload.get("body") or "", source=value)
