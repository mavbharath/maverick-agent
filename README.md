# Local Ollama Coding Agent

A small, auditable, **local-first coding agent powered exclusively by Ollama**. It can inspect a repository, make approved edits, run checks, and keep a local audit trail. No cloud LLM fallback. No telemetry. No API keys.

## What it includes

- Ollama `/api/chat` tool-calling loop
- Repository path confinement (including symlink resolution)
- Explicit read, search, patch, write, shell, and finish tools
- Human approval before edits and mutating commands (`--yes` is opt-in)
- Fail-closed blocks for dangerous shell patterns
- Bounded steps, timeouts, and tool output
- `AGENTS.md` / `.local-coder.md` repository instructions
- Local JSONL session logs in `<repo>/.local-coder/`
- Python standard-library runtime; no cloud SDKs

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/download)
- A tool-capable coding model. Recommended starting point: `qwen2.5-coder:7b` (use a larger variant if your machine can handle it).

## Install

```bash
cd ~/Downloads/local-ollama-coding-agent
chmod +x install.sh run.sh
./install.sh
ollama pull qwen2.5-coder:7b
```

Start Ollama if it is not already running:

```bash
ollama serve
```

## Quick start

```bash
./run.sh --repo /path/to/your/project doctor
./run.sh --repo /path/to/your/project run "Find and fix the failing tests, then run the relevant test suite"
```

Choose another local model:

```bash
./run.sh --repo ./my-project --model qwen2.5-coder:14b run "Add input validation and tests"
```

For trusted disposable repositories, skip per-write approval:

```bash
./run.sh --repo ./sandbox --yes run "Implement the TODOs and run tests"
```

Disable shell execution entirely:

```bash
./run.sh --repo ./project --no-shell run "Review this code for correctness"
```

## Commands

```text
local-coder [global options] doctor
local-coder [global options] models
local-coder [global options] run TASK...
```

Important options:

- `--repo PATH`: hard workspace boundary
- `--model NAME`: installed Ollama model
- `--host URL`: Ollama endpoint; defaults to loopback
- `--max-steps N`: bounded agent turns
- `--timeout SECONDS`: model and command timeout
- `--yes`: auto-approve writes/mutating commands
- `--no-shell`: remove shell access from the model

## Safety model

This is an engineering guardrail, not a magical sandbox. By default it:

1. Resolves every file path and rejects repository escapes.
2. Requests approval before every file mutation.
3. Blocks `sudo`, forced recursive deletion, dangerous Git operations, host-management commands, host paths, and download-to-shell patterns.
4. Scrubs common secret-suffixed environment variables from child processes.
5. Stops after a fixed step limit.

For stronger isolation, run it in a container or VM and mount only the target repository. Do **not** use `--yes` on an important repository before reviewing the project and committing clean work.

## Workflows

See [`WORKFLOWS.md`](WORKFLOWS.md) for the full workflow catalog and exact commands.

## Architecture

```text
CLI -> Config -> CodingAgent -> OllamaClient
                    |              (localhost only)
                    v
              ToolRegistry -> Workspace / ApprovalGate / shell safety
                    |
                    v
              local JSONL SessionLog
```

The pieces stay boring on purpose. One authoritative Ollama path, one tool registry, one workspace boundary—no speculative provider maze doing interpretive dance behind your back.

## References and provenance

This implementation is original code informed by publicly inspectable patterns:

- Code Puppy: https://github.com/mpfaffenberger/code_puppy (MIT)
- CognitionAI public organization: https://github.com/CognitionAI
- CognitionAI public repositories: https://github.com/orgs/CognitionAI/repositories
- Public SWE-bench result/methodology artifacts: https://github.com/CognitionAI/devin-swebench-results (MIT)

Devin's core implementation is not present in those public repositories. This project does **not** copy or claim access to Devin internals. The reusable ideas here are generic, inspectable agent patterns: bounded workflows, explicit tools, environment interaction, verification, audit logs, and approval boundaries.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

## License

MIT. See [`LICENSE`](LICENSE).
