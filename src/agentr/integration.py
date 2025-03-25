from abc import ABC, abstractmethod
from agentr.store import Store
import httpx

"""
Integration defines how a Application needs to authorize.
It is responsible for authenticating application with the service provider.
Supported integrations:
- AgentR Integration
- API Key Integration
"""

class Integration(ABC):
    def __init__(self, name: str, store: Store = None):
        self.name = name
        self.store = store

    @abstractmethod
    def get_credentials(self):
        pass

    @abstractmethod
    def set_credentials(self, credentials: dict):
        pass

class ApiKeyIntegration(Integration):
    def __init__(self, name: str, store: Store = None, **kwargs):
        super().__init__(name, store, **kwargs)

    def get_credentials(self):
        credentials = self.store.get(self.name)
        return credentials

    def set_credentials(self, credentials: dict):
        self.store.set(self.name, credentials)

class AgentRIntegration(Integration):
    def __init__(self, name: str, api_key: str, **kwargs):
        super().__init__(name, **kwargs)
        self.api_key = api_key
        self.base_url = "https://api.agentr.dev/v1"

    def get_credentials(self):
        response = httpx.get(f"{self.base_url}/{self.name}/credentials", headers={"Authorization": f"Bearer {self.api_key}"})
        return response.json()

    def authorize(self):
        response = httpx.post(f"{self.base_url}/{self.name}/authorize", headers={"Authorization": f"Bearer {self.api_key}"})
        url = response.json()["url"]
        return url
