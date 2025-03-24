from abc import ABC, abstractmethod
from mcp.server.fastmcp import FastMCP

from agentr.applications.zenquotes.app import ZenQuoteApp
from agentr.store import Store

class Server(FastMCP, ABC):
    """
    Server is responsible for managing the applications and the store
    It also acts as a router for the applications, and exposed to the client

    """
    def __init__(self, name: str, description: str, store: Store, **kwargs):
        self.store = store
        super().__init__(name, description, **kwargs)


class TestServer(Server):
    """
    Test server for development purposes
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apps_list = ["zenquotes"]
        self.__load_apps()

    def __load_apps(self):
        self.apps = []
        for app in self.apps_list:
            if app == "zenquotes":
                app = ZenQuoteApp(store=self.store)
                tools = app.list_tools()
                self.add_tool(tools[0])
