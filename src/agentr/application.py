from abc import ABC, abstractmethod
from agentr.store import Store
import httpx

class Application(ABC):
    def __init__(self, name: str, **kwargs):
        self.name = name

    @abstractmethod
    def list_tools(self):
        pass


class APIApplication(Application):
    def __init__(self, name: str, store: Store, **kwargs):
        super().__init__(name, **kwargs)
        self.store = store

    def _get_headers(self):
        return {}
    
    def _get(self, url, params=None):
        headers = self._get_headers()
        response = httpx.get(url, headers=headers, params=params)
        return response
    
    def _post(self, url, data):
        headers = self._get_headers()
        response = httpx.post(url, headers=headers, data=data)
        return response

    def _put(self, url, data):
        headers = self._get_headers()
        response = httpx.put(url, headers=headers, data=data)
        return response

    def _delete(self, url):
        headers = self._get_headers()
        response = httpx.delete(url, headers=headers)
        return response

    def validate(self):
        pass
    
    def authorize(self):
        pass

    @abstractmethod
    def list_tools(self):
        pass