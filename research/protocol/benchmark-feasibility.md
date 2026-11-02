# Benchmark feasibility decision

## SWE-bench Lite: not feasible in the current free Colab runtime

The Colab feasibility cell reported 98.0 GiB free disk and Docker unavailable. The official SWE-bench harness documents a minimum of 120 GB free storage and recommends 16 GB RAM. Do not report official SWE-bench results from this runtime.

## Goldset: next candidate, pending one-record Colab verification

Goldset contains real Python bug-fix records and a test that distinguishes the buggy parent commit from the author's fix. Its verifier clones a repository, materializes both commits, overlays the regression test into the buggy tree, and runs the test without Docker. Its release contains 896 records across 352 projects (corpus snapshot dated 2026-08-19 in its datasheet); the corpus is published under CC BY 4.0 while each code record retains the source project's listed permissive license and attribution.

For the planned retrieval comparison, both conditions must receive the same Goldset specification and buggy source. The retrieval condition may additionally receive code retrieved from the buggy repository at the parent commit. The verifier's regression test is the test oracle and must never be included in the prompt. Goldset tasks are specification-and-code records rather than complete GitHub issue reports, so describe the study as specification-driven bug repair if this candidate is adopted.

The initial Colab feasibility check used a file-level record committed after 2025-01-01. The paired agent pilot now selects a function-level record from the same post-release date window to reduce the prompt and model memory requirement on the T4. This date filter is after the public release of Qwen2.5-Coder (2024-09-19), reducing direct benchmark-answer exposure to that fixed model snapshot. It does not prove that all benchmark information is absent from pretraining. The corpus and model commit SHA, selected record fingerprint, license, parent/fix revisions, interpreter, and pass/fail/skip output must be logged.

**Colab feasibility result (2026-11-02):** Goldset revision `fe4f9bfbcb46637481242af2315c6b59951710b4`; record `4e210790188a0356` (`erikrose/parsimonious`, fix date 2025-01-02, MIT) verified as `passed 1, failed 0, skipped 0` in the user's Colab. This confirms the official one-record oracle runs there. The notebook now includes the next one-record agent pilot under matched no-retrieval and retrieval conditions. Retrieved chunks exclude both the target source file and the benchmark test file, while both conditions receive the same specification and buggy source.

**Status:** Goldset is the benchmark candidate. Freeze it only after the matched agent pilot completes and its run records confirm both conditions used the same model revision, task, and test protocol.

## Sources

- SWE-bench official harness requirements: <https://github.com/SWE-bench/SWE-bench/blob/main/docs/reference/harness.md>
- Goldset repository and verifier description: <https://github.com/andysalvo/goldset>
- Goldset datasheet: <https://github.com/andysalvo/goldset/blob/main/DATASHEET.md>
- Qwen2.5-Coder public release date: <https://qwenlm.github.io/blog/qwen2.5-coder/>
