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

        self.base_url = "https://auth.agentr.dev"
        self.user_id = "default"
    
    def _create_session_token(self):
        url = "https://auth.agentr.dev/connect/sessions"
        body = {
            "end_user": {
                "id": self.user_id,
            },
            "allowed_integrations": [self.name]
        }
        response = httpx.post(url, headers={"Authorization": f"Bearer {self.api_key}"}, json=body)
        data = response.json()
        print(data)
        return data["data"]["token"]
    
    def _get_authorize_url(self):
        session_token = self._create_session_token()
        return f"https://auth.agentr.dev/oauth/connect/{self.name}?connect_session_token={session_token}"
    
    def get_connection_by_owner(self):
        url = f"https://auth.agentr.dev/connection?endUserId={self.user_id}"
        response = httpx.get(url, headers={"Authorization": f"Bearer {self.api_key}"})
        if response.status_code == 200:
            connections = response.json()["connections"]
            for connection in connections:
                if connection["provider_config_key"] == self.name:
                    return connection["connection_id"]
        return None

    def set_credentials(self, credentials: dict):
        raise NotImplementedError("AgentR Integration does not support setting credentials. Visit the authorize url to set credentials.")

    def get_credentials(self):
        connection_id = self.get_connection_by_owner()
        logger.info(f"Connection ID: {connection_id}")
        if connection_id:
            response = httpx.get(f"{self.base_url}/connection/{connection_id}?provider_config_key={self.name}", headers={"Authorization": f"Bearer {self.api_key}"})
            data = response.json()
            return data.get("credentials")
        return None

    def authorize(self):
        url = self._get_authorize_url()
        return f"Please authorize the application by clicking the link {url}"
