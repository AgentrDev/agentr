from abc import ABC, abstractmethod
from agentr.integration import Integration
import httpx

class Application(ABC):
    """
    Application is collection of tools that can be used by an agent.
    """
    def __init__(self, name: str, **kwargs):
        self.name = name

    @abstractmethod
    def list_tools(self):
        pass


class APIApplication(Application):
    """
    APIApplication is an application that uses an API to interact with the world.
    """
    def __init__(self, name: str, integration: Integration = None, **kwargs):
        super().__init__(name, **kwargs)
        self.integration = integration

    def _get_headers(self):
        return {}
    
    def _get(self, url, params=None):
        headers = self._get_headers()
        response = httpx.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response
    
    def _post(self, url, data):
        headers = self._get_headers()
        response = httpx.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response

    def _put(self, url, data):
        headers = self._get_headers()
        response = httpx.put(url, headers=headers, json=data)
        response.raise_for_status()
        return response

    def _delete(self, url):
        headers = self._get_headers()
        response = httpx.delete(url, headers=headers)
        response.raise_for_status()
        return response

    def validate(self):
        pass
    
    @abstractmethod
    def list_tools(self):
        pass