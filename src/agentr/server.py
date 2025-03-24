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

    @abstractmethod
    def _load_apps(self):
        pass


class TestServer(Server):
    """
    Test server for development purposes
    """
    def __init__(self, apps_list: list[str] = [], **kwargs):
        super().__init__(**kwargs)
        self.apps_list = apps_list
        self._load_apps()

    def _load_apps(self):
        for app in self.apps_list:
            if app == "zenquotes":
                app = ZenQuoteApp(store=self.store)
                tools = app.list_tools()
                self.add_tool(tools[0])
