from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .agent import run_task
from .ollama_client import OllamaClient


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="local-coder", description="Local Ollama coding agent")
    p.add_argument("--repo", required=True, help="Repository/workspace root")
    p.add_argument("--model", default=os.environ.get("LOCAL_CODER_MODEL", "qwen2.5-coder:7b"))
    p.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    p.add_argument("--max-steps", type=int, default=12)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--yes", action="store_true", help="Skip approval prompts for edits and mutating shell commands")
    p.add_argument("--no-shell", action="store_true", help="Disable shell tool")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check Ollama connectivity, model, and workspace")
    sub.add_parser("models", help="List locally available Ollama models")
    r = sub.add_parser("run", help="Run a task")
    r.add_argument("task", nargs="+", help="Task prompt")
    return p


def main() -> int:
    args = parser().parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        print(f"Repository directory does not exist: {repo}", file=sys.stderr)
        return 2
    client = OllamaClient(args.host.rstrip("/"), args.model, args.timeout)
    if args.command == "doctor":
        print(f"Workspace: {repo}")
        try:
            tags = client.get("/api/tags")
            models = [m.get("name", "") for m in tags.get("models", [])]
            print(f"Ollama reachable: {args.host}")
            print("Installed models:")
            for model in models:
                print(f"  - {model}")
            if not any(m == args.model or m.startswith(args.model + ":") for m in models):
                print(f"Model not found: {args.model}\nRun: ollama pull {args.model}")
                return 1
            print(f"Model ready: {args.model}")
            return 0
        except Exception as exc:
            print(f"Ollama check failed: {exc}", file=sys.stderr)
            print("Start Ollama with: ollama serve", file=sys.stderr)
            return 1
    if args.command == "models":
        try:
            for model in client.get("/api/tags").get("models", []):
                print(model.get("name", ""))
            return 0
        except Exception as exc:
            print(f"Could not list models: {exc}", file=sys.stderr)
            return 1
    task = " ".join(args.task)
    try:
        run_task(repo=repo, client=client, task=task, max_steps=max(1, args.max_steps),
                 allow_shell=not args.no_shell, auto_approve=args.yes)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Agent failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
