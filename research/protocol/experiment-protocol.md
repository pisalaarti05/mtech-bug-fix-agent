# Goldset retrieval comparison protocol

**Protocol version:** 1.0  
**Status:** Frozen prospectively on 2026-11-24, before the final evaluation run. The Nov. 3 pilot and Nov. 24 refinement are development results and are not part of this evaluation.

## Research question

For one fixed open-weight model and a fixed set of Goldset Python repair tasks, does adding repository-code retrieval change the rate of generated replacements that pass the task's regression test?

## Benchmark and sample

- Benchmark: public Goldset release at commit `fe4f9bfbcb46637481242af2315c6b59951710b4`.
- Sample manifest: [`goldset-evaluation-sample.csv`](goldset-evaluation-sample.csv). It contains 30 records from 30 distinct repositories, selected before running either final condition.
- Eligible pool: records whose fix commit date is later than 2024-09-19, excluding every task previously used by this project (`1f881a956841fe4f`, `d2509b7ca26e23a0`, `ce753d7eea707e6a`, `4e210790188a0356`, and `cbafae4011f8117b`). At the pinned snapshot this leaves 310 records across 142 repositories.
- Selection rule: for each eligible repository, select the record with the smallest SHA-256 digest of `mtech-goldset-eval-v1:<fingerprint>`. Rank those repositories by the SHA-256 digest of `mtech-goldset-eval-v1:<repo>` and take the first 30. This yields one record per repository without choosing tasks based on generated outcomes.
- Goldset describes a separate held-out portion that is not published. This study therefore uses a newly selected subset from the public release, not Goldset's hidden held-out portion. The date filter reduces exposure to model pretraining data but does not prove that the model never saw related code.
- Do not replace a selected record based on model outcome. Before scoring, the Goldset oracle must show the buggy revision fails and the reference fix passes. Record verification skips or invalid oracles as exclusions. If a record cannot be scored in one condition because of an environment error, exclude it from the paired denominator and report the reason; generated patch failures remain scored failures.

## Compared conditions

Run each selected record once under each condition using the same loaded model, fixed prompt, token limits, and test setup. Run no retrieval first, then retrieval, in manifest order.

**A. No retrieval:** give the model the task specification and exact buggy target code only.

**B. Retrieval:** give the same specification and buggy target code plus up to three repository-code chunks. Retrieval uses the buggy repository checkout, BM25 ranking, 80-line chunks with 12-line overlap, and at most one chunk per source file. Exclude the target file, the regression test file, tests, documentation, examples, generated files, and dependency directories. The retrieval query is the specification plus buggy target code. Do not expose the reference fix to either condition.

Both conditions use the prompt and benchmark implementation in project commit `d54f9fbeac811c62957ad3d36a64933e58caaf5d`. The prompt requests only a complete replacement for the exact target and asks the model to preserve names, signatures, decorators, base classes, annotations, and indentation unless the specification requires a change. Do not provide test-failure feedback or a second generation attempt in this primary comparison. Do not change prompt, retriever, top-k, or sample after seeing final outcomes.

## Model and decoding

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`.
- Immutable model snapshot: `c03e6d358207e414f1eca0bb1891e29f1db0e242`.
- Load in 4-bit NF4 with double quantization, float16 compute, and automatic device mapping.
- Input limit: 3072 tokens. Output limit: 768 tokens.
- Greedy decoding (`do_sample=False`); retain the model's default generation settings otherwise.
- Keep this model and snapshot fixed for every task and condition. If the Colab runtime cannot load this exact snapshot, stop and resolve availability before starting the final evaluation; do not silently step down to another model.

## Test and scoring procedure

For each condition and task, use the pinned Goldset runner to create a disposable checkout, confirm the recorded regression test fails on the buggy parent and passes on the reference fix, apply the model's replacement, and run the same regression test. The reference patch is only a test-environment check; it is never added to either prompt or retrieval context.

- **Pass:** the model replacement applies and all required Goldset regression tests pass.
- **Repair failure:** the replacement is empty or invalid, does not match the target, fails the regression test, or causes collection/runtime failure after the buggy and reference checks have validated the environment.
- **Unscored:** Goldset checkout, buggy/reference validation, or another environment prerequisite is unavailable. Report the reason and keep it out of the paired denominator.

Store one JSON record per task-condition under `artifacts/runs/goldset_final/`. Preserve the resource report, model snapshot, package versions, Goldset revision, retrieved paths/chunks, generated replacement, test IDs/results, elapsed time, and token counts. Download and retain the final run-artifact archive outside the temporary Colab filesystem before ending the runtime. Do not commit cloned benchmark repositories or large raw artifacts to GitHub.

## Outcomes and analysis

- **Primary outcome:** test-verified pass rate in each condition among paired scorable records.
- **Primary comparison:** paired difference in pass rates (retrieval minus no retrieval), with the counts of pairs passing in both, failing in both, and discordant pairs. Report an exact McNemar test and a 95% confidence interval for the paired difference; treat the small sample as exploratory.
- **Secondary outcomes:** patch application rate, number of retrieved chunks and files, retrieval hit on the target module when measurable, input/output tokens, generation time, test runtime, and skip/exclusion counts.
- Report raw numerators and denominators; do not turn skipped records into failures or successes. Make no general claim from the three-task development runs.

## Runtime record

At the start of every fresh Colab runtime, rerun the resource report. The last successful report found a Tesla T4, 14.46 GiB free VRAM, and 112.54 GiB free disk; the exact 7B snapshot loaded successfully. Record the final run's actual Python, CUDA, GPU, PyTorch, Transformers, Accelerate, BitsAndBytes, Goldset, and project-code revisions. If the available runtime differs materially, stop before final scoring and revise this protocol before execution.

## Limitations

This is a 30-task exploratory comparison from a public benchmark release, not a sample of all production defects or Goldset's unpublished held-out set. One record per repository limits within-repository clustering. Goldset tests certify only the recorded regression behavior, not complete program correctness. The 3B pilot and 7B development refinement used different model sizes and must not be compared as a controlled model-size or refinement effect.

## Sources

- Goldset pinned source and datasheet: <https://github.com/andysalvo/goldset/tree/fe4f9bfbcb46637481242af2315c6b59951710b4>
- Qwen2.5-Coder release information: <https://qwenlm.github.io/blog/qwen2.5-coder/>
- Qwen2.5-Coder series release information: <https://qwenlm.github.io/blog/qwen2.5-coder-family/>
