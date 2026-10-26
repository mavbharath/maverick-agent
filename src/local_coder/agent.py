from __future__ import annotations

import json
from pathlib import Path

from .ollama_client import OllamaClient
from .tools import TOOLS, ToolRunner

SYSTEM = """
You are a careful local coding agent.

Rules:
- Work only inside the supplied repository.
- Inspect files before editing.
- Follow AGENTS.md and .local-coder.md if present.
- Prefer small, focused changes.
- Never claim tests passed unless tool output proves it.
- Use the provided tools for repository operations.
- Paths must be repository-relative.
- Obtain approval through the tool approval process before edits.
- Do not bypass safety checks.
- Explain findings with evidence and file paths.
- Finish with a concise, readable summary.
"""


def run_task(
    repo: Path,
    client: OllamaClient,
    task: str,
    max_steps: int,
    allow_shell: bool,
    auto_approve: bool,
) -> None:
    runner = ToolRunner(repo, allow_shell, auto_approve)

    instructions = []

    for name in ("AGENTS.md", ".local-coder.md"):
        path = repo / name

        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")[:12000]
                instructions.append(f"\n--- {name} ---\n{content}")
            except OSError as exc:
                print(f"Warning: Could not read {name}: {exc}")

    messages = [
        {
            "role": "system",
            "content": (
                SYSTEM
                + "\nWorkspace: "
                + str(repo)
                + "\n"
                + "\n".join(instructions)
            ),
        },
        {
            "role": "user",
            "content": task,
        },
    ]

    for step in range(max_steps):
        print(f"\n[Agent] Step {step + 1}/{max_steps}")

        response = client.chat(messages, TOOLS)
        message = response.get("message", {})

        if not isinstance(message, dict):
            print("[Agent] Invalid response from Ollama.")
            return

        messages.append(message)

        calls = message.get("tool_calls") or []

        # Compatibility fallback: some models return a tool call as JSON text.
        if not calls:
            content = message.get("content", "").strip()
            try:
                candidate = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                # Extract a JSON object embedded in explanatory model text.
                candidate = None
                decoder = json.JSONDecoder()
                for index, char in enumerate(content):
                    if char == "{":
                        try:
                            candidate, _ = decoder.raw_decode(content[index:])
                            break
                        except json.JSONDecodeError:
                            continue

            try:
                if isinstance(candidate, dict) and isinstance(candidate.get("name"), str):
                    name = candidate["name"]
                    args = candidate.get("arguments", {})
                    known_tools = {
                        tool.get("function", {}).get("name")
                        for tool in TOOLS
                    }
                    if name in known_tools and isinstance(args, dict):
                        calls = [{
                            "function": {
                                "name": name,
                                "arguments": args
                            }
                        }]
            except (json.JSONDecodeError, TypeError):
                pass

        if not calls:
            content = message.get("content", "").strip()
            if content:
                print("\n=== Agent Response ===\n")
                print(content)
            else:
                print("[Agent] Model returned neither text nor tool calls.")
            return

        for call in calls:
            function = call.get("function", {})
            name = function.get("name", "")
            args = function.get("arguments", {})

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            if not isinstance(args, dict):
                args = {}

            print(f"[Agent] Tool requested: {name}")

            if name == "finish":
                summary = str(args.get("summary", "Task finished."))

                # Do not terminate immediately after finish.
                # Ask the model to produce the final readable response.
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The tool workflow has finished. "
                            "Now provide the actual final answer to the original task. "
                            "Use the evidence gathered from tool results. "
                            "Include relevant file paths, findings, and limitations. "
                            "Do not call more tools. "
                            "Workflow summary: "
                            + summary
                        ),
                    }
                )

                response = client.chat(messages, [])
                final_message = response.get("message", {})
                final_content = final_message.get("content", "").strip()

                print("\n=== Agent Final Answer ===\n")
                print(final_content or summary)
                return

            try:
                result = runner.call(name, args)
            except Exception as exc:
                result = f"Tool error ({name}): {type(exc).__name__}: {exc}"

            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False, default=str)

            # Return tool output to the model so it can reason about
            # the actual repository contents.
            messages.append(
                {
                    "role": "tool",
                    "content": result,
                }
            )

    print(
        f"\n[Agent] Reached max step limit ({max_steps}). "
        f"Review the tool output and session log at {runner.audit_file}."
    )
