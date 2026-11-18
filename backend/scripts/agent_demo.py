"""Watch the AI decide which MCP tools to call, step by step.

Run from the backend folder (venv active):
    python -m scripts.agent_demo "Which documents do we have, and how long is paternity leave?"
"""

import argparse
import asyncio
import json
import textwrap

from app.services.tool_agent import get_tool_agent


async def main(question: str) -> None:
    result = await get_tool_agent().run(question)

    print(f"Question: {question}\n")
    if not result.tool_calls:
        print("(The AI answered without using any tool.)\n")
    for number, call in enumerate(result.tool_calls, start=1):
        status = "ERROR" if call.is_error else "ok"
        print(f"Tool call {number}: {call.name}({json.dumps(call.arguments)})  → {status}, {call.duration_ms:.0f} ms")
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
