from agentr.server import TestServer
from agentr.store import MemoryStore

store = MemoryStore()

mcp = TestServer(name="Test Server", description="Test Server", store=store, apps_list=["zenquotes"])

if __name__ == "__main__":
    mcp.run()