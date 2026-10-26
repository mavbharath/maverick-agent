# Workflow Catalog

All model inference stays on the configured Ollama endpoint. The default is `http://127.0.0.1:11434`.

## 1. First-time setup

```bash
cd ~/Downloads/local-ollama-coding-agent
chmod +x install.sh run.sh
./install.sh
ollama pull qwen2.5-coder:7b
./run.sh --repo . doctor
```

Flow: install isolated Python CLI -> pull local model -> verify Ollama and model.

## 2. Inspect and explain a repository

```bash
./run.sh --repo /path/to/repo --no-shell run \
  "Inspect the architecture and explain the request flow. Do not edit files."
```

Flow: list -> search -> read -> finish. Shell is unavailable.

## 3. Fix a bug

```bash
./run.sh --repo /path/to/repo run \
  "Reproduce the reported bug, identify the root cause, add a regression test, fix it, and run focused tests."
```

Flow: inspect -> reproduce -> edit with approval -> test -> summarize evidence.

## 4. Implement a feature

```bash
./run.sh --repo /path/to/repo run \
  "Implement FEATURE. Follow AGENTS.md, keep the diff focused, add tests, and run relevant checks."
```

Put project rules in `/path/to/repo/AGENTS.md` or `.local-coder.md` before running.

## 5. Repair failing tests

```bash
./run.sh --repo /path/to/repo run \
  "Run the failing test suite, diagnose failures from evidence, make the smallest correct fix, and rerun it."
```

Do not say “make tests green at any cost”; that invites symptom-hiding nonsense. Root causes only, puppy rules.

## 6. Refactor safely

```bash
./run.sh --repo /path/to/repo run \
  "Refactor MODULE to separate I/O from core logic without changing behavior. Run existing tests before and after."
```

Flow: baseline tests -> inspect callers -> incremental patches -> tests -> diff review.

## 7. Review-only workflow

```bash
./run.sh --repo /path/to/repo --no-shell run \
  "Review the current code for correctness, security, and maintainability. Cite file paths and lines. Do not edit."
```

For a Git diff review while retaining read-only shell commands:

```bash
./run.sh --repo /path/to/repo run \
  "Review git diff. Do not edit. Report actionable findings ordered by severity."
```

## 8. Documentation workflow

```bash
./run.sh --repo /path/to/repo run \
  "Update README usage to match the current CLI. Verify all commands against the source."
```

Flow: inspect implementation -> patch documentation -> optionally run `--help` -> finish.

## 9. Trusted sandbox autonomy

```bash
./run.sh --repo /tmp/disposable-project --yes run \
  "Build the requested prototype, add tests, and run them."
```

`--yes` removes approval prompts but does not remove path checks, shell blocks, timeouts, or the step limit. Use only in a clean, disposable, or version-controlled workspace.

## 10. Model selection

```bash
./run.sh --repo . models
./run.sh --repo /path/to/repo --model qwen2.5-coder:14b doctor
./run.sh --repo /path/to/repo --model qwen2.5-coder:14b run "TASK"
```

You can set the default:

```bash
export LOCAL_CODER_MODEL=qwen2.5-coder:14b
```

## 11. Remote Ollama on your LAN

```bash
./run.sh --host http://192.168.1.50:11434 --repo /path/to/repo doctor
```

This remains Ollama-only but is no longer machine-local. Protect the endpoint with network controls; Ollama's API should not be exposed raw to the internet.

## 12. Failure recovery

- Interrupted run: restart with a concise task containing current status.
- Bad edit: reject it at the approval prompt, or use your normal version-control rollback.
- Step limit: inspect `<repo>/.local-coder/session-*.jsonl`, then rerun with a narrower task or a controlled `--max-steps` increase.
- Ollama unavailable: start `ollama serve`, then run `doctor`.
- Model missing: run `ollama pull MODEL`, then run `doctor`.

## Agent internal workflow

Each task follows one path:

1. Load repository instructions.
2. Send task, tool schemas, and bounded policy to Ollama.
3. Execute model tool calls through the registry.
4. Confine paths and evaluate shell safety.
5. Request approval for mutation unless `--yes` was explicit.
6. Return tool evidence to Ollama.
7. Stop on `finish`, model halt, interruption, error, or step limit.
8. Persist a local JSONL audit trail.
