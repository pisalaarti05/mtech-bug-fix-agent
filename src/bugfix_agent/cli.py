"""Command-line interface for one issue-driven repair experiment."""
from __future__ import annotations
import argparse
from pathlib import Path
from .issue import load_issue
from .runner import run_repair

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and validate a bug-fix suggestion in a temporary repository clone.")
    parser.add_argument("--repo", required=True, help="Public Git repository URL")
    parser.add_argument("--issue", required=True, help="Bug report text or public GitHub issue URL")
    parser.add_argument("--model", required=True, help="Hugging Face model ID (select after the Colab pilot)")
    parser.add_argument("--commit", help="Repository commit to evaluate; defaults to the current remote default branch")
    parser.add_argument("--output", default="artifacts/runs", help="Folder for local JSON run records")
    parser.add_argument("--no-retrieval", action="store_true", help="Run the controlled no-retrieval baseline")
    parser.add_argument("--top-k", type=int, default=6, help="Number of code chunks to retrieve")
    parser.add_argument("--test-command", help="Test command to run in the temporary clone, for example: python -m pytest")
    parser.add_argument("--test-timeout", type=int, default=600, help="Maximum test runtime in seconds")
    return parser

def main() -> None:
    args = build_parser().parse_args()
    if args.top_k < 1 or args.test_timeout < 1:
        raise SystemExit("--top-k and --test-timeout must be positive numbers.")
    issue = load_issue(args.issue)
    output = run_repair(repository_url=args.repo, issue=issue, model_id=args.model, output_dir=Path(args.output), commit=args.commit, use_retrieval=not args.no_retrieval, top_k=args.top_k, test_command=args.test_command, test_timeout=args.test_timeout)
    print(f"Run record saved to: {output}")

if __name__ == "__main__":
    main()
