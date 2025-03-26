from abc import ABC, abstractmethod
from typing import Literal
from mcp.server.fastmcp import FastMCP
from agentr.integration import AgentRIntegration, ApiKeyIntegration
from agentr.store import EnvironmentStore, MemoryStore
from pydantic import BaseModel
from loguru import logger

class StoreConfig(BaseModel):
    type: Literal["memory", "environment"]

class IntegrationConfig(BaseModel):
    name: str
    type: Literal["api_key", "agentr"]
    credentials: dict | None = None
    store: StoreConfig | None = None

class AppConfig(BaseModel):
    name: str
    integration: IntegrationConfig | None = None

class Server(FastMCP, ABC):
    """
    Server is responsible for managing the applications and the store
    It also acts as a router for the applications, and exposed to the client

    """
    def __init__(self, name: str, description: str, **kwargs):
        super().__init__(name, description, **kwargs)

    @abstractmethod
    def _load_apps(self):
        pass


class TestServer(Server):
    """
    Test server for development purposes
    """
    def __init__(self, name: str, description: str, apps_list: list[AppConfig] = [], **kwargs):
        super().__init__(name, description=description, **kwargs)
        self.apps_list = [AppConfig.model_validate(app) for app in apps_list]
        self._load_apps()
    
    def _get_store(self, store_config: StoreConfig):
        if store_config.type == "memory":
            return MemoryStore()
        elif store_config.type == "environment":
            return EnvironmentStore()
        return None

    def _get_integration(self, integration_config: IntegrationConfig):
        if integration_config.type == "api_key":
            store = self._get_store(integration_config.store)
            integration = ApiKeyIntegration(integration_config.name, store=store)
            if integration_config.credentials:
                integration.set_credentials(integration_config.credentials)
            return integration
        elif integration_config.type == "agentr":
            integration = AgentRIntegration(integration_config.name, api_key=integration_config.credentials.get("api_key") if integration_config.credentials else None)
            return integration
        return None
    
    def _load_app(self, app_config: AppConfig):
        name = app_config.name
        if name == "zenquotes":
            from agentr.applications.zenquotes.app import ZenQuoteApp
            return ZenQuoteApp()
        elif name == "tavily":
            from agentr.applications.tavily.app import TavilyApp
            integration = self._get_integration(app_config.integration)
            return TavilyApp(integration=integration)
        elif name == "github":
            from agentr.applications.github.app import GithubApp
            integration = self._get_integration(app_config.integration)
            return GithubApp(integration=integration)
        elif name == "google-calendar":
            from agentr.applications.google_calendar.app import GoogleCalendarApp
            integration = self._get_integration(app_config.integration)
            return GoogleCalendarApp(integration=integration)
        elif name == "gmail":
            from agentr.applications.google_mail.app import GmailApp
            integration = self._get_integration(app_config.integration)
            return GmailApp(integration=integration)
        elif name == "resend":
            from agentr.applications.resend.app import ResendApp
            integration = self._get_integration(app_config.integration)
            return ResendApp(integration=integration)
        elif name == "reddit":
            from agentr.applications.reddit.app import RedditApp
            integration = self._get_integration(app_config.integration)
            return RedditApp(integration=integration)
        else:
            return None
            
    def _load_apps(self):
        logger.info(f"Loading apps: {self.apps_list}")
        for app_config in self.apps_list:
            app = self._load_app(app_config)
            if app:
                tools = app.list_tools()
                for tool in tools:
                    self.add_tool(tool)

                
