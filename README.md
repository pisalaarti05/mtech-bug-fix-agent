# Repository-Aware Bug-Fix Agent

An MTech research prototype that compares bug-fix suggestions from one language model with and without automatically retrieved Python code. It works on a disposable clone, records the exact commit, validates the suggested patch, and can run a test command before saving a local JSON record.

The research plan remains the source of truth for the model, benchmark, Colab feasibility, and final experiment. Goldset is the current small-benchmark candidate; one Colab verification is still required before it is frozen.

## Current implementation

The first pipeline step is in place:

- Load bug text or a public GitHub issue.
- Clone a public Git repository into a temporary folder and optionally select an exact commit.
- Retrieve Python code chunks with a small BM25 search method.
- Run either the retrieval condition or the no-retrieval baseline.
- Ask a selected Hugging Face causal language model for a unified diff.
- Validate and apply that diff only in the temporary clone.
- Optionally run a test command and save the prompt, retrieved chunks, patch, commit, and test result as JSON.

Model libraries are optional until the Colab model pilot is complete. The retriever and input handling use only Python's standard library.

## Local setup

Python 3.10 or newer and Git are required.

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --editable .

The current local environment can run the command-line interface and retrieval without model packages:

    bugfix-agent --help

## Run a repair

After selecting a model that fits the Colab pilot, install model support in the environment that will run inference:

    python -m pip install --editable ".[model]"

Then run one issue. Use a public GitHub repository URL and either issue text or a public issue URL.

    bugfix-agent --repo https://github.com/OWNER/REPOSITORY.git --issue "Describe the bug here" --model MODEL_ID --test-command "python -m pytest"

The test command executes repository code in the temporary clone. Review the repository and its test instructions before running it. The original repository is not modified. Run bugfix-agent --help to see all options, including a fixed commit and --no-retrieval.

## Goldset pilot

The Colab notebook includes a one-record Goldset runner that reuses the selected model for a matched no-retrieval/retrieval comparison. Install `python -m pip install --editable ".[model,benchmark]"` for local setup. The benchmark helper uses Goldset's verifier to confirm the recorded test fails on the buggy revision and passes on the reference revision before scoring the generated replacement. It excludes the target source and test file from retrieved context and saves each condition as a separate JSON record. This is a feasibility pilot; it is not a full benchmark result.

Run records are saved under artifacts/runs/, which is ignored by Git. Do not put access tokens or private repository URLs in committed files.

## Google Colab

Colab is used for the feasibility pilot and model inference. The SWE-bench Lite official harness did not fit the available runtime (98 GiB free disk, Docker unavailable). The notebook now checks one Goldset record as a smaller Python benchmark candidate. Goldset prompts use a behavior specification and buggy code, not a full GitHub issue report; report results with that scope if adopted.

## Project structure

- PROJECT_PLAN.md — implementation, research, and reporting roadmap.
- src/bugfix_agent/ — Python application.
- research/ — literature review, experiment protocol, and results notes.
- data/ — dataset notes and local data; benchmark data is not committed.
- notebooks/ — Colab and evaluation notebooks.
- configs/ — experiment configuration files.
- workspaces/ — temporary repository checkouts and local setup files; ignored by Git.
- artifacts/ — local run outputs; ignored by Git.
