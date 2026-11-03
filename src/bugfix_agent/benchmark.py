"""Run one Goldset repair record with or without repository retrieval."""
from __future__ import annotations

import ast
import json
import re
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import TYPE_CHECKING

from .retrieval import collect_chunks, retrieve

if TYPE_CHECKING:
    from .model import HuggingFaceModel


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.fullmatch(r"```(?:python)?\s*\n([\s\S]*?)\n?```", text, re.IGNORECASE)
    return match.group(1).strip() if match else text


def _prompt(record: dict[str, object], retrieved: list[dict[str, object]]) -> str:
    if record["granularity"] == "file":
        code_kind = "file"
    else:
        try:
            nodes = ast.parse(str(record["source_before"])).body
        except SyntaxError:
            nodes = []
        target_nodes = [
            node for node in nodes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        if len(target_nodes) == 1 and isinstance(target_nodes[0], ast.ClassDef):
            code_kind = "class"
        elif len(target_nodes) == 1 and isinstance(target_nodes[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
            code_kind = "function"
        else:
            code_kind = "code block"
    spec_source = record.get("spec_source")
    spec_label = "documented behavior" if spec_source == "docstring" else "bug-fix task specification"
    parts = [
        "You repair Python code. Make the smallest change that satisfies the specification.",
        f"The exact replacement target is a {code_kind} from {record['repo']}.",
        f"\nSPECIFICATION ({spec_label}):\n{record['spec']}",
        f"\nBUGGY CODE TO REPLACE:\n{record['source_before']}",
        "\nReturn only the complete corrected replacement for the exact buggy code block above. Do not return imports, tests, documentation examples, retrieved snippets, neighboring definitions, a diff, an explanation, or a Markdown fence.",
        "Preserve its name, signature, decorators, base classes, annotations, and indentation unless the specification explicitly requires changing them. Do not invent a class base, import, or identifier; use only names visible in the target code.",
    ]
    if retrieved:
        snippets = [
            f"\n--- {item['path']}:{item['start_line']}-{item['end_line']} ---\n{item['text']}"
            for item in retrieved
        ]
        parts.append("\nADDITIONAL REPOSITORY CODE (the target file and test file are excluded):\n" + "".join(snippets))
    return "\n".join(parts)


def run_goldset_record(
    record: dict[str, object],
    model: HuggingFaceModel,
    output_dir: Path,
    *,
    use_retrieval: bool = True,
    top_k: int = 6,
    corpus_revision: str | None = None,
) -> Path:
    """Generate one replacement and score it against the record's regression test.

    Goldset provides the disposable before/after trees and test runner. Its
    reference fix is used only to confirm the test environment, never in the
    prompt or retrieval index.
    """
    if not isinstance(record.get("fingerprint"), str):
        raise ValueError("The Goldset record is missing its fingerprint.")
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")
    try:
        from goldset.exec import Checkout, ladder_for, run_tests, run_tests_anywhere, test_names
    except ImportError as exc:
        raise RuntimeError(
            "Goldset's pinned benchmark helpers are unavailable. Rerun the notebook's "
            "Goldset verification/setup cell to install its pinned source checkout."
        ) from exc

    from .model import HuggingFaceModel as _HuggingFaceModel  # avoid runtime import for users of the core package

    if not isinstance(model, _HuggingFaceModel):
        raise TypeError("model must be a HuggingFaceModel instance.")

    started = time.perf_counter()
    test_ids = record.get("fail_to_pass")
    if not isinstance(test_ids, list) or not test_ids:
        raise ValueError("The Goldset record has no fail-to-pass test IDs.")
    names = test_names(test_ids)
    results: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "Goldset",
        "benchmark_fingerprint": record["fingerprint"],
        "benchmark_corpus_revision": corpus_revision,
        "repository": record.get("repo"),
        "project_license": record.get("license"),
        "fix_date": record.get("committed_at"),
        "requested_commit": record.get("parent"),
        "reference_fix_commit": record.get("commit"),
        "granularity": record.get("granularity"),
        "model_id": model.model_id,
        "model_revision": model.revision,
        "condition": "retrieval" if use_retrieval else "no_retrieval",
        "top_k": top_k if use_retrieval else 0,
        "test_file": record.get("test_file"),
        "test_ids": test_ids,
        "test_status": "not_run",
        "retrieved_chunks": [],
    }

    with Checkout(record) as checkout:
        if checkout.error:
            results["test_status"] = "skipped"
            results["skip_reason"] = checkout.error
        else:
            before, python_version = run_tests_anywhere(
                checkout.before, record["test_file"], names, ladder_for(record)
            )
            results["test_python"] = python_version or "runtime default"
            if not before.ran:
                results["test_status"] = "skipped"
                results["skip_reason"] = before.detail
            elif not before.failures:
                results["buggy_revision_test_status"] = "passed"
                results["test_status"] = "skipped"
                results["skip_reason"] = "The benchmark test did not fail on the buggy revision."
            else:
                results["buggy_revision_test_status"] = "failed_as_expected"
                results["buggy_revision_failing_tests"] = sorted(before.failures)
                reference = run_tests(checkout.after, record["test_file"], names, python=python_version)
                if not reference.ran or reference.failures:
                    results["reference_fix_test_status"] = "failed_or_unavailable"
                    results["test_status"] = "skipped"
                    results["skip_reason"] = "The reference fix did not pass in this Colab environment."
                else:
                    results["reference_fix_test_status"] = "passed"
                    target = Path(checkout.source_path(checkout.before))
                    if not target.is_file() or record["source_before"] not in target.read_text(encoding="utf-8", errors="replace"):
                        results["test_status"] = "skipped"
                        results["skip_reason"] = "Goldset's recorded buggy source was not found in the checkout."
                    else:
                        retrieved: list[dict[str, object]] = []
                        if use_retrieval:
                            chunks = collect_chunks(Path(checkout.before))
                            target_rel = target.relative_to(checkout.before).as_posix()
                            test_file = str(record["test_file"])
                            chunks = [
                                chunk for chunk in chunks
                                if chunk.path != target_rel and chunk.path != test_file
                            ]
                            # Retrieval may use only information also given to
                            # the no-retrieval condition: the spec and buggy code.
                            query = f"{record.get('spec', '')}\n{record.get('source_before', '')}"
                            ranked = retrieve(query, chunks, limit=len(chunks)) if chunks else []
                            seen_paths: set[str] = set()
                            for chunk, score in ranked:
                                if chunk.path in seen_paths:
                                    continue
                                seen_paths.add(chunk.path)
                                retrieved.append(
                                    {"path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line, "score": score, "text": chunk.text}
                                )
                                if len(retrieved) == top_k:
                                    break
                        prompt = _prompt(record, retrieved)
                        results["prompt"] = prompt
                        results["retrieved_chunks"] = retrieved
                        response = _strip_code_fence(model.generate(prompt))
                        results["model_response"] = response
                        results["generation_usage"] = model.last_usage
                        if not response:
                            results["test_status"] = "failed"
                            results["failure_reason"] = "The model returned an empty replacement."
                        elif not checkout.apply(checkout.before, response):
                            results["test_status"] = "failed"
                            results["failure_reason"] = "The model replacement did not match the recorded buggy source."
                        else:
                            after = run_tests(checkout.before, record["test_file"], names, python=python_version)
                            if not after.ran:
                                # The unmodified buggy revision and the reference
                                # fix both ran successfully above. A collection
                                # error after replacing the code is therefore a
                                # failed generated repair, not an environment skip.
                                results["test_status"] = "failed"
                                results["failure_reason"] = (
                                    "Tests could not collect or run after the model replacement: "
                                    + after.detail
                                )
                            elif after.failures:
                                results["test_status"] = "failed"
                                results["failing_tests"] = sorted(after.failures)
                            else:
                                results["test_status"] = "passed"

    results["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    software_versions: dict[str, str] = {}
    for package in ("torch", "transformers", "accelerate", "bitsandbytes", "huggingface_hub", "goldset"):
        try:
            software_versions[package] = package_version(package)
        except PackageNotFoundError:
            continue
    results["software_versions"] = software_versions
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{stamp}_{record['fingerprint']}_{results['condition']}.json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
