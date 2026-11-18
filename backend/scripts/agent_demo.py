"""Watch the AI decide which MCP tools to call, step by step — and approve risky actions.

Run from the backend folder (venv active):
    python -m scripts.agent_demo "Which documents do we have, and how long is paternity leave?"
    python -m scripts.agent_demo "Save a note called 'Team lunch': Friday 13:00 in the canteen."
"""

import argparse
import asyncio
import json
import textwrap

from app.services.tool_agent import AgentResult, get_tool_agent


def ask_human(result: AgentResult) -> dict[str, bool]:
    """Show each pending action and ask y/n. Anything but 'y' means NO (safe default)."""
    decisions = {}
    for pending in result.pending:
        warning = "⚠ DESTRUCTIVE, cannot be undone" if pending.destructive else "changes data"
        print(f"\nThe AI wants to run: {pending.name}({json.dumps(pending.arguments)})  [{warning}]")
        # lstrip("﻿"): PowerShell puts an invisible byte-order mark before piped text.
        answer = input("Approve? [y/N] ").strip().lstrip("﻿").lower()
        decisions[pending.call_id] = answer == "y"
        print("  → approved" if decisions[pending.call_id] else "  → rejected")
    return decisions


async def main(question: str) -> None:
    agent = get_tool_agent()
    result = await agent.run(question)
    while result.status == "needs_approval":
        result = await agent.resume(result, ask_human(result))

    print(f"\nQuestion: {question}\n")
    if not result.tool_calls:
        print("(The AI answered without using any tool.)\n")
    for number, call in enumerate(result.tool_calls, start=1):
        status = "ERROR" if call.is_error else "ok"
        approval = "" if call.approval == "auto" else f", {call.approval} by you"
        print(f"Tool call {number}: {call.name}({json.dumps(call.arguments)})  → {status}{approval}, {call.duration_ms:.0f} ms")
        print(textwrap.indent(textwrap.shorten(call.result, 220), "    "))
    print("\nAnswer:")
    print(textwrap.indent(textwrap.fill(result.answer, 90), "  "))
    usage = result.usage.total_tokens if result.usage else "?"
    print(f"\n{result.steps} AI call(s), {len(result.tool_calls)} tool call(s), {usage} tokens"
          + (" — stopped early (max steps)" if result.stopped_early else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP tool-calling agent demo")
    parser.add_argument("question", nargs="?", default="Which documents do we have, and how long is paternity leave?")
    asyncio.run(main(parser.parse_args().question))
