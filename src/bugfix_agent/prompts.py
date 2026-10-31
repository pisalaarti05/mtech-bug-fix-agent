"""Prompts used by both experimental conditions."""
from __future__ import annotations
from .issue import Issue
from .retrieval import CodeChunk

def repair_prompt(issue: Issue, context: list[CodeChunk] | None = None) -> str:
    sections = [
        "You are helping repair a Python repository. Make the smallest defensible change for the reported bug.",
        "Return only a unified diff that applies from the repository root. Do not use Markdown fences.",
        "If the report lacks enough information, return an empty response rather than inventing files.",
        "\nBUG REPORT\n" + issue.prompt_text,
    ]
    if context:
        snippets = [f"\n--- {chunk.path}:{chunk.start_line}-{chunk.end_line} ---\n{chunk.text}" for chunk in context]
        sections.append("\nRETRIEVED REPOSITORY CODE\n" + "".join(snippets))
    return "\n".join(sections)
