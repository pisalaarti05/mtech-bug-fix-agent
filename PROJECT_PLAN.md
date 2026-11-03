# MTech Project and Research Plan

## 1. Purpose

This plan is the working guide for implementing the MTech project, evaluating it as a research study, updating the final project report, and preparing a journal submission. It is deliberately scoped for a practical, timely implementation while retaining a reproducible experimental comparison.

This is a plan, not a claim that the proposed system works or that the research gap is already proven. Confirm the scope and resolve the decisions marked below before implementation begins.

## 2. Project definition

### Working title

**Repository-Aware Bug-Fix Suggestions Using Code Retrieval and an Open-Weight Language Model**

### Working scope

The user supplies a GitHub repository and a bug report or GitHub issue. The system analyzes the issue, locates relevant code, generates a patch, runs tests in a temporary working copy, and returns the patch and test outcome for human review.

The initial scope is issue-driven bug repair. It does not include autonomous discovery of unknown bugs, multiple programming languages, model training or fine-tuning, multi-agent orchestration, or automatic commits and pushes to GitHub. Those features can be reconsidered only if the core experiment is complete and there is time.

### Research objective

Measure whether repository-code retrieval improves test-verified bug-fix success for one open-weight model on a feasible Python bug-fix benchmark, and characterize the quality and resource cost of the retrieval-enabled workflow. The current Goldset candidate presents a behavior specification and buggy code rather than a full issue report.

### Primary research question

**RQ1.** On the selected Python bug-fix benchmark, does adding repository-code retrieval improve test-verified repair success compared with giving the same model the benchmark specification and buggy target code without additional retrieved repository snippets?

### Supporting questions

**RQ2.** How often does retrieval surface files changed by the reference fix?

**RQ3.** What additional runtime and token use are associated with retrieval and test-guided refinement?

The paper contribution is expected to be a transparent empirical study in a resource-constrained open-weight setting, not a claim that RAG or automated repair is a new idea. The related-work review must check for closely matching studies before the contribution is finalized.

## 3. Proposed system workflow

1. Accept a repository URL and issue URL or issue text.
2. Resolve the repository state to evaluate. For benchmark cases, use the pre-fix commit and record its commit hash.
3. Parse the issue into a concise repair task while retaining the original text.
4. Inspect and index supported source files, excluding generated files and irrelevant large folders.
5. Retrieve a small, fixed-budget set of relevant code chunks. Start with one simple retrieval method; add a second only if the pilot supports it.
6. Ask one selected open-weight model to produce a patch in a machine-readable unified-diff format.
7. Validate and apply the patch in a temporary checkout, never in the user's original working tree.
8. Run the issue-specific tests and available regression tests in the benchmark environment.
9. If tests fail, allow at most one refinement attempt using the failure output.
10. Return the proposed diff, files retrieved, tests run, and test outcome. The user decides whether to apply or publish the patch.

The workflow is agentic through its coordinated observe, retrieve, patch, test, and bounded-refinement steps. A sequential controller is sufficient; a multi-agent design is not required.

## 4. Decisions required before implementation

| Decision | Initial direction | How to finalize |
|---|---|---|
| Bug input | User-supplied issue | Confirm that autonomous bug discovery is out of scope. |
| Programming language | Python | Confirm benchmark tasks and repository mix. |
| Benchmark | Goldset is the Colab-compatible candidate after SWE-bench proved too resource-intensive | One post-release record passed its Goldset verifier in Colab. The matched agent pilot is still required before freezing the benchmark. Goldset prompts are specifications plus buggy source, not full GitHub issue reports. |
| Model | One open-weight code-capable model selected per runtime from a fixed model ladder | Every fresh runtime must report free disk, system RAM, GPU name, total/free VRAM, and PyTorch/CUDA state before any weight download. Use the same selected model and limits for both conditions; log its resolved immutable revision. |
| Retrieval | Begin with a simple repository-code retriever | Select chunking and retrieval settings using pilot tasks; freeze them before final evaluation. |
| Evaluation size | Pilot first, then the largest feasible fixed subset | Estimate runtime and model availability from pilot; document exclusions and the reason for the final sample size. |
| Execution environment | Google Colab for inference and benchmark experiments; GitHub for version control | Keep exact runtime and package versions in experiment records. |

Do not assume that every benchmark can run unchanged in Colab. The first SWE-bench Lite feasibility check found only 98 GiB free disk and no Docker in the user's runtime, so its official harness cannot run there. Goldset is the current candidate: one post-release record passed its verifier in Colab without Docker. Its tasks supply a behavioral specification and buggy code, not a full issue report. The next gate is to restart from a resource report, select a model tier from current free GPU memory and disk, and complete a matched no-retrieval/retrieval pilot. Use records fixed after the selected model's public release where feasible, and record exact corpus/model revisions. A runtime restart invalidates the prior resource report and requires this check again.

## 5. Implementation phases and completion criteria

### Phase 0 — Scope approval and feasibility

- Confirm issue-driven scope and the limits above.
- Review recent primary literature on repository retrieval, code repair, issue-resolution benchmarks, and open-weight models.
- Test one candidate benchmark case in Colab, including repository checkout and tests.
- At every fresh Colab runtime, measure free disk, system RAM, GPU model, total/free VRAM, and PyTorch/CUDA state before downloading weights.
- Select from the resource-gated model ladder in `research/protocol/benchmark-feasibility.md`; record the selected model, token limits, and resolved model revision.
- Test candidate model loading and one inference call.

**Complete when:** the resource report is captured, an eligible model is selected, and that model completes one inference call; the benchmark and model can run a small end-to-end feasibility pilot, or a documented alternative is chosen.

### Phase 1 — Baseline repair pipeline

- Implement repository and issue input handling.
- Pin and log the evaluated repository commit.
- Build prompt construction and structured patch output.
- Apply and validate patches only in a disposable checkout.
- Save per-instance inputs, model settings, proposed patch, test commands, logs, and result.

**Complete when:** the baseline can be run repeatedly on pilot tasks and its outputs are auditable.

### Phase 2 — Retrieval-enabled pipeline

- Parse supported source files and divide them into reproducible code chunks.
- Index chunks and retrieve issue-relevant code using the chosen lightweight method.
- Record ranked retrieved chunks, source file and line range, and retrieval configuration.
- Supply a fixed context budget to the model.

**Complete when:** retrieval output is inspectable and the same instance can be replayed with fixed settings.

### Phase 3 — Bounded test-feedback refinement

- Run the generated patch through benchmark tests.
- If it fails, pass a concise test failure summary to the model for one refinement attempt.
- Track initial and refined patch outcomes separately.

**Complete when:** test execution and refinement produce clear per-attempt records and do not alter source repositories outside the temporary workspace.

### Phase 4 — Pilot and protocol freeze

- Run a small set spanning more than one repository and bug type where available.
- Check test setup, execution time, model failures, patch formatting, and data leakage risks.
- Freeze the benchmark subset, prompts, decoding parameters, retrieval method, context limit, test rules, and exclusion criteria before the full run.

**Complete when:** the protocol is written in `research/protocol/experiment-protocol.md` and no tuning is performed on final evaluation cases.

### Phase 5 — Full controlled evaluation

- Run two primary conditions on the same instances: (A) same model without retrieved repository code; (B) same model with retrieved code.
- Keep model version, issue text, decoding settings, patch format, test environment, and output limits consistent.
- Include test-guided refinement either in both conditions or as a separately reported ablation; do not give only one condition extra repair attempts.
- Save raw outputs and logs locally; do not commit benchmark repositories, credentials, model tokens, or large generated artifacts.

**Complete when:** every included case has a result or a documented exclusion, and the run can be reproduced from the recorded configuration.

### Phase 6 — Analysis and MTech report

- Calculate metrics from saved per-instance records.
- Inspect failures and representative success cases.
- State limitations and threats to validity.
- Update Part I claims, architecture, algorithms, datasets, and evaluation metrics to match what was actually implemented.
- Write the final MTech report only after results are available; never describe proposed results as achieved results.

**Complete when:** all reported values can be regenerated from saved data and the report distinguishes measurements from interpretation.

### Phase 7 — Research paper and journal submission preparation

- Recheck the literature for overlap and refine the research gap based on the implemented experiment.
- Write the paper with enough detail to reproduce the benchmark subset, model setup, prompts, retrieval configuration, test procedure, and exclusions.
- Report negative and mixed results as well as positive ones.
- Select a journal after the paper is drafted; verify scope, peer-review process, indexing claims, fees, and submission requirements from authoritative sources.
- Submit only after the authors approve the final manuscript and venue.

**Complete when:** the paper makes a bounded, evidence-backed contribution and the target venue has passed legitimacy and affordability checks.

## 6. Experimental design

### Conditions

- **No-retrieval baseline:** issue input and the same model, without automatically retrieved repository snippets.
- **Retrieval condition:** the same issue and model, augmented with repository code retrieved by the selected method.
- **Optional refinement ablation:** compare first patch with one test-feedback refinement, applied consistently and reported separately.

The baseline must be described precisely. It must not secretly receive manually selected gold files while the retrieval condition does not, or vice versa.

### Primary outcome

- **Test-verified success rate:** proportion of evaluated issues where the generated patch passes the benchmark's required issue-specific tests. Report the numerator and denominator, not only a percentage.

### Supporting outcomes

- **Reference-file Recall@k:** whether at least one file changed by the reference fix appears among the top-k retrieved files. This is a localization proxy, not proof that the patch is correct.
- **Patch validity:** whether the output parses as a patch and applies cleanly.
- **Regression result:** whether the required regression suite passes, where available.
- **Runtime and token use:** measured per issue and by condition.
- **Refinement effect:** initial versus refined outcomes, where refinement is included.

Do not use classification accuracy, precision, recall, or F1 as the main patch-correctness metrics unless a defensible classification labeling scheme is designed. A plausible patch is not counted as correct unless it meets the stated validation rule.

### Reproducibility and leakage controls

- Evaluate code at the benchmark's pre-fix commit.
- Keep the reference patch and post-fix code unavailable to the agent.
- Log repository and benchmark identifiers, commit hashes, model identifier/version, prompts, retrieval settings, test commands, and environment versions.
- Define exclusions before the full run; report every exclusion and reason.
- Use repeat runs if the model is stochastic and resources permit; otherwise state deterministic settings and sampling limitations.
- Report confidence intervals or other uncertainty estimates appropriate to the sample size.

## 7. Research paper outline

1. **Abstract:** problem, controlled setup, key measured results, and bounded conclusion.
2. **Introduction:** issue-driven repair challenge, research question, and contributions.
3. **Related work:** APR, LLM repair, repository retrieval, RAG for code, benchmarks.
4. **System:** architecture and bounded repair workflow.
5. **Methodology:** benchmark selection, model, retrieval, conditions, metrics, protocol, and leakage controls.
6. **Results:** test-verified success, localization, runtime/token results, and uncertainty.
7. **Discussion:** when retrieval helped or hurt and why.
8. **Threats to validity:** benchmark representativeness, sample size, model/version dependence, test coverage, and Colab variability.
9. **Conclusion:** what the evidence supports and next steps.

## 8. Repository and data practices

- Keep source code, experiment protocol, and paper drafts version-controlled.
- Keep benchmark data, cloned repositories, credentials, caches, model weights, and large run outputs out of Git unless licensing and size have been checked and inclusion is necessary.
- Store a small, non-sensitive run manifest and aggregate results in the repository; preserve raw logs separately as appropriate.
- Use a `.env.example` for variable names only; never commit `.env`, access tokens, or private repository URLs.
- Use GitHub issues/PRs for project tracking after the remote repository is selected.

## 9. Definition of project completion

The MTech project is complete when the scoped agent runs end-to-end on the selected benchmark subset, generates and validates patches in an isolated environment, the controlled comparison is reproducible, results and limitations are reported honestly, and the final MTech report matches the implementation.

The paper is ready for submission when the related-work review supports a specific contribution, the methods and results are auditable, limitations are clear, and a legitimate affordable journal has been verified. Publication acceptance is outside the project's control and cannot be guaranteed.

## 10. Resource-first operating rule

A runtime restart is a new hardware environment. Always run the notebook resource cell first and inspect its report before downloading model weights. The current pilot ladder is Qwen2.5-Coder-7B-Instruct when at least 11 GiB GPU memory is free and 20 GiB disk remains; 3B when at least 6 GiB GPU memory and 12 GiB disk remain; 1.5B when at least 4.5 GiB GPU memory and 8 GiB disk remain. Without CUDA or below these limits, stop before model download and select a suitable GPU runtime. Use the token budgets printed by the resource cell. If loading fails from memory pressure, record the error, restart, remeasure, and step down one tier. Never change models between paired conditions. Record the resource report, model ID and immutable model revision, quantization, token limits, and runtime errors in run artifacts. These thresholds are conservative pilot starting points, not a guarantee of successful loading.

## 11. Beginner hand-holding and error recovery

The user is new to coding and needs explicit guidance at every stage. Never assume they know what a notebook cell, runtime, terminal command, package, variable, or traceback means. Give one step at a time with the exact notebook section/cell heading to open, what to click or paste, what successful output should look like, and what to send back if it differs. Keep the sequence explicit and do not ask them to invent troubleshooting suggestions.

When an error occurs, take ownership of diagnosis: inspect the saved notebook output and repository code, explain the cause in plain language, choose a fix or a feasible alternative, implement and verify the change locally, push notebook/code updates to GitHub when Colab needs them, then give the user only the next action. If the first route is blocked by Colab limits, choose the next viable route (smaller model, smaller task, fewer tokens, CPU/GPU runtime change, or another benchmark) and update this plan before proceeding. Never present a failed/skipped condition as success. Preserve the resource-first rule after every runtime restart.

For the current restarted Colab runtime, guide the user through these notebook sections in order:

1. Connect to a Colab runtime and select a GPU runtime if available.
2. Run the first code cell, which reports RAM, free disk, GPU name, and total/free GPU memory, then recommends the model tier. Stop if it reports an error or insufficient resources; explain the next route.
3. Run **Download and install the project**.
4. Run **Confirm the command is ready**.
5. Run **Verify one record from the smaller Goldset benchmark**. Continue only if it reports one pass and zero failures/skips.
6. Run the model-libraries installation cell.
7. Run **Load the selected model and make one short request**. Continue only if a model revision and non-empty response are printed.
8. Run **Run one Goldset task through the agent with and without retrieval**. Review both outputs and their run records; both conditions must complete before calling the paired pilot successful.

Skip **Check one SWE-bench Lite task and Colab capacity**; that feasibility check is already complete and the official harness is not supported by the available runtime. After each step, inspect the output before directing the user to the next step. If runtime restarts, begin again at step 1.

## 12. Approval gate

This plan is pending the user's confirmation of the issue-driven scope and research direction. Implementation begins only after that confirmation.
