from agentr.integrations.base import Integration
from agentr.store import Store

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