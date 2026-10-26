from __future__ import annotations

import difflib
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MAX_READ = 24000
MAX_OUTPUT = 12000
DANGEROUS = re.compile(r"(^|[;&|]\s*)(sudo\b|rm\s+-rf\b|git\s+(reset\s+--hard|clean\s+-fd|push\s+--force)|mkfs\b|shutdown\b|reboot\b)|>\s*/(etc|usr|bin|sbin)/", re.I)


def schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}}

TOOLS = [
    schema("list_files", "List files under a relative path in the repository.", {"path": {"type": "string"}}, ["path"]),
    schema("search_text", "Search repository text for a literal string. Skips .git, .venv, caches and build folders.", {"query": {"type": "string"}, "path": {"type": "string"}}, ["query", "path"]),
    schema("read_file", "Read a UTF-8 text file inside the repository.", {"path": {"type": "string"}}, ["path"]),
    schema("patch_file", "Replace an exact unique text snippet in a file. Requires human approval unless --yes was supplied.", {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, ["path", "old_text", "new_text"]),
    schema("write_file", "Create or overwrite a UTF-8 text file. Requires human approval unless --yes was supplied.", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    schema("run_shell", "Run a shell command in the repository. Use only for relevant checks. Mutating commands require approval.", {"command": {"type": "string"}}, ["command"]),
    schema("finish", "Finish the task and provide a concise summary of actions and evidence.", {"summary": {"type": "string"}}, ["summary"]),
]


class ToolRunner:
    def __init__(self, repo: Path, allow_shell: bool, auto_approve: bool):
        self.repo = repo.resolve()
        self.allow_shell = allow_shell
        self.auto_approve = auto_approve
        self.audit_dir = self.repo / ".local-coder"
        self.audit_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.audit_file = self.audit_dir / f"session-{stamp}.jsonl"

    def _path(self, value: str) -> Path:
        p = Path(value)
        target = (self.repo / p).resolve() if not p.is_absolute() else p.resolve()
        if target != self.repo and self.repo not in target.parents:
            raise ValueError("Path escapes the repository boundary")
        return target

    def _approve(self, action: str) -> bool:
        if self.auto_approve:
            return True
        answer = input(f"\nApprove {action}? [y/N] ").strip().lower()
        return answer in {"y", "yes"}

    def _audit(self, name: str, args: dict, result: str) -> None:
        record = {"time": datetime.now(timezone.utc).isoformat(), "tool": name, "arguments": args,
                  "result": result[:2000]}
        with self.audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def call(self, name: str, args: dict) -> str:
        try:
            result = self._call(name, args)
        except Exception as exc:
            result = f"ERROR: {type(exc).__name__}: {exc}"
        self._audit(name, args, result)
        print(f"\n[{name}]\n{result[:2000]}")
        return result[:MAX_OUTPUT]

    def _call(self, name: str, a: dict) -> str:
        if name == "list_files":
            root = self._path(a["path"])
            if not root.exists(): return "Path does not exist"
            if root.is_file(): return str(root.relative_to(self.repo))
            items = []
            for p in sorted(root.rglob("*")):
                if any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"} for part in p.parts): continue
                items.append(str(p.relative_to(self.repo)) + ("/" if p.is_dir() else ""))
                if len(items) >= 250: break
            return "\n".join(items) or "(empty)"
        if name == "search_text":
            query, root = a["query"], self._path(a["path"])
            if not query: return "Search query is empty"
            files = [root] if root.is_file() else root.rglob("*")
            found, count = [], 0
            for p in files:
                if not p.is_file() or any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist", ".local-coder"} for part in p.parts): continue
                try:
                    lines = p.read_text(encoding="utf-8").splitlines()
                except (UnicodeError, OSError): continue
                for i, line in enumerate(lines, 1):
                    if query.casefold() in line.casefold():
                        found.append(f"{p.relative_to(self.repo)}:{i}: {line[:300]}")
                        count += 1
                        if count >= 100: return "\n".join(found)
            return "\n".join(found) or "No matches found"
        if name == "read_file":
            p = self._path(a["path"])
            if not p.is_file(): return "File does not exist"
            return p.read_text(encoding="utf-8")[:MAX_READ]
        if name in {"patch_file", "write_file"}:
            p = self._path(a["path"])
            if name == "patch_file":
                if not p.is_file(): return "File does not exist"
                old, new = a["old_text"], a["new_text"]
                current = p.read_text(encoding="utf-8")
                if not old: return "Refusing empty old_text"
                if current.count(old) != 1: return f"Expected exactly one match; found {current.count(old)}. No changes made."
                updated = current.replace(old, new, 1)
            else:
                updated = a["content"]
            diff = "".join(difflib.unified_diff((p.read_text(encoding="utf-8").splitlines(True) if p.exists() else []).copy(), updated.splitlines(True), fromfile=str(p.relative_to(self.repo)), tofile=str(p.relative_to(self.repo))))
            print(diff[:6000] if diff else "(new file or no textual diff)")
            if not self._approve(f"write to {p.relative_to(self.repo)}"):
                return "Denied by user; no changes made"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(updated, encoding="utf-8")
            return f"Wrote {p.relative_to(self.repo)} ({len(updated)} characters)"
        if name == "run_shell":
            if not self.allow_shell: return "Shell disabled by --no-shell"
            command = a["command"].strip()
            if not command: return "Empty command"
            if DANGEROUS.search(command): return "Blocked by safety policy. Inspect and run any necessary administrative/destructive command manually."
            mutating = bool(re.search(r"\b(rm|mv|cp|mkdir|touch|chmod|chown|git\s+(add|commit|checkout|switch|restore|reset|clean)|pip\s+install|npm\s+install)\b|\btee\b|\bsed\s+-i\b", command))
            if mutating and not self._approve(f"shell command: {command}"):
                return "Denied by user"
            proc = subprocess.run(command, shell=True, cwd=self.repo, text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=60, env={k:v for k,v in os.environ.items() if not k.upper().endswith(("TOKEN", "SECRET", "PASSWORD", "API_KEY"))})
            return f"exit_code={proc.returncode}\n{proc.stdout[-MAX_OUTPUT:]}"
        if name == "finish":
            return "TASK_FINISHED: " + a.get("summary", "Completed")
        return f"Unknown tool: {name}"
