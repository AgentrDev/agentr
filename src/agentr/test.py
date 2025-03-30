from agentr.server import AgentRServer


mcp = AgentRServer(name="Test Server", description="Test Server")

async def test():
    tools = await mcp.list_tools()
    from pprint import pprint
    pprint(tools)
    result = await mcp.call_tool("get_today_events", {})
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())