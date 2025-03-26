from abc import ABC, abstractmethod
import os
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



class NangoIntegration(Integration):
    def __init__(self, user_id, integration_id):
        self.integration_id = integration_id
        self.user_id = user_id
        self.nango_secret_key = os.getenv("NANGO_SECRET_KEY")

    def _create_session_token(self):
        url = "https://api.nango.dev/connect/sessions"
        body = {
            "end_user": {
                "id": self.user_id,
            },
            "allowed_integrations": [self.integration_id]
        }
        response = httpx.post(url, headers={"Authorization": f"Bearer {self.nango_secret_key}"}, json=body)
        data = response.json()
        return data["data"]["token"]
    
    def get_authorize_url(self):
        session_token = self._create_session_token()
        return f"https://api.nango.dev/oauth/connect/{self.integration_id}?connect_session_token={session_token}"

    def get_connection_by_owner(self, user_id):
        url = f"https://api.nango.dev/connection?endUserId={user_id}"
        response = httpx.get(url, headers={"Authorization": f"Bearer {self.nango_secret_key}"})
        if response.status_code == 200:
            connections = response.json()["connections"]
            for connection in connections:
                if connection["provider_config_key"] == self.integration_id:
                    return connection["connection_id"]
        return None

class AgentRIntegration(Integration):
    def __init__(self, name: str, api_key: str = None, **kwargs):
        super().__init__(name, **kwargs)
        self.api_key = api_key or os.getenv("AGENTR_API_KEY")
        if not self.api_key:
            raise ValueError("api_key is required")
        self.base_url = "https://api.agentr.dev"
        self.user_id = "default"

    def get_credentials(self):
        response = httpx.get(f"{self.base_url}/integrations/{self.name}/credentials", headers={"Authorization": f"Bearer {self.api_key}"})
        return response.json()

    def authorize(self):
        response = httpx.post(f"{self.base_url}/integrations/{self.name}/authorize", headers={"Authorization": f"Bearer {self.api_key}"})
        url = response.json()["url"]
        return {"url": url, "text": "Please authorize the application by clicking the link {url}"}
