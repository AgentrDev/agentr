from agentr.server import LocalServer
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
mcp = LocalServer(name="Test Server", description="Test Server", apps_list=apps_list)


async def test():
    tools = await mcp.list_tools()
    from pprint import pprint
    pprint(tools)
    result = await mcp.call_tool("star_repository", {"repo_full_name": "manojbajaj95/config"})
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())