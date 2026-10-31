# Application Package

The first pipeline implementation is available as a local command-line program. It accepts a public repository and issue, runs one of two comparison conditions (with or without retrieved code), requests a unified diff from a user-selected Hugging Face model, applies it only in a temporary clone, optionally runs tests, and saves a JSON record.

The retriever, issue parser, temporary checkout, patch validator, model adapter, runner, and command-line interface are split into separate modules. Model selection and benchmark selection remain gated on the Colab feasibility pilot in the project plan.
