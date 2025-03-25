from agentr.server import TestServer
from agentr.store import MemoryStore

store = MemoryStore()
apps_list = [
    {
        "name": "tavily",
        "integration": {
            "name": "tavily_api_key",
            "type": "api_key",
            "store": {
                "type": "environment",
            }
        },        
    },
    {
        "name": "zenquotes",
        "integration": None
    },
    {
        "name": "github",
        "integration": {
            "name": "github",
            "type": "agentr",
        }
    }
]
mcp = TestServer(name="Test Server", description="Test Server", apps_list=apps_list)

async def test():
    tools = await mcp.list_tools()
    print(tools)
    result = await mcp.call_tool("search", {"query": "python"})
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())