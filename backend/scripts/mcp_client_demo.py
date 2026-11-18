"""Act as an MCP HOST: start Shema's MCP server as a subprocess and talk to it over stdio.

This is exactly what apps like Cursor or Claude Desktop do with MCP servers.

Run from the backend folder (venv active):
    python -m scripts.mcp_client_demo
    python -m scripts.mcp_client_demo "What is Project KESTREL?"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

BACKEND = Path(__file__).resolve().parent.parent


async def main(question: str) -> None:
    # 1. How to start the server: same Python, our module, run from the backend folder
    #    (so it finds backend/.env for its own API keys).
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server.server"],
        cwd=BACKEND,
    )

    async with Client(params) as client:
        # 2. Handshake done: who is on the other side?
        info = client.server_info
        print(f"Connected to MCP server: {info.name} {info.version}\n")

        # 3. Discovery: what does the server offer?
        tools = await client.list_tools()
        print("TOOLS (the AI can call these):")
        for tool in tools.tools:
            params_list = ", ".join(tool.input_schema.get("properties", {}))
            print(f"  - {tool.name}({params_list}): {tool.description.splitlines()[0]}")

        resources = await client.list_resources()
        print("\nRESOURCES (the app can read these):")
        for resource in resources.resources:
            print(f"  - {resource.uri}  {resource.description}")

        prompts = await client.list_prompts()
        print("\nPROMPTS (templates the user can pick):")
        for prompt in prompts.prompts:
            print(f"  - {prompt.name}: {prompt.description}")

        # 4. Call a tool, the way an AI would after deciding it needs one.
        print(f'\nCALL search_documents(query="{question}", top_k=3)')
        result = await client.call_tool("search_documents", {"query": question, "top_k": 3})
        if result.is_error:
            print("  tool error:", result.content[0].text)
        else:
            for hit in result.structured_content["result"]:
                page = f", page {hit['page_number']}" if hit["page_number"] else ""
                print(f"  {hit['similarity']:.3f}  [{hit['document_title']}{page}]  {hit['content'][:80]}…")

        # 5. Read a resource.
        catalog = await client.read_resource("shema://documents")
        print("\nREAD shema://documents")
        print("  " + catalog.contents[0].text.replace("\n", "\n  "))

        # 6. A tool error: the server refuses bad input with a clear message.
        bad = await client.call_tool("search_documents", {"query": "x", "top_k": 99})
        print(f"\nCALL search_documents(top_k=99) → is_error={bad.is_error}: {bad.content[0].text}")
        print("\nRaw tool schema the AI sees:")
        print(json.dumps(tools.tools[0].input_schema, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP client demo")
    parser.add_argument("question", nargs="?", default="What is Project KESTREL?")
    asyncio.run(main(parser.parse_args().question))
