from abc import ABC, abstractmethod
import os
import sys

from loguru import logger
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
    def authorize(self):
        pass
    
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

    def authorize(self):
        return {"text": "Please configure the environment variable {self.name}_API_KEY"}



class AgentRIntegration(Integration):
    def __init__(self, name: str, api_key: str = None, **kwargs):
        super().__init__(name, **kwargs)
        self.api_key = api_key or os.getenv("AGENTR_API_KEY")
        if not self.api_key:
            logger.error("API key for AgentR is missing. Please visit https://agentr.dev to create an API key, then set it as AGENTR_API_KEY environment variable.")
            raise ValueError("AgentR API key required - get one at https://agentr.dev")
        self.base_url = os.getenv("AGENTR_BASE_URL", "https://api.agentr.dev")
    
    
    def set_credentials(self, credentials: dict| None = None):
        return self.authorize()
        # raise NotImplementedError("AgentR Integration does not support setting credentials. Visit the authorize url to set credentials.")

    def get_credentials(self):
        response = httpx.get(
            f"{self.base_url}/api/{self.name}/credentials/",
            headers={
                "accept": "application/json",
                "X-API-KEY": self.api_key
            }
        )
        response.raise_for_status()
        data = response.json()
        return data

    def authorize(self):
        response = httpx.get(
            f"{self.base_url}/api/{self.name}/authorize/",
            headers={
                "X-API-KEY": self.api_key
            }
        )
        response.raise_for_status()
        url = response.json()
        return f"Please authorize the application by clicking the link {url}"
