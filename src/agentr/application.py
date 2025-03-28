from abc import ABC, abstractmethod

from loguru import logger
from agentr.exceptions import NotAuthorizedError
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
        try:
            headers = self._get_headers()
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response
        except NotAuthorizedError as e:
            logger.warning(f"Reddit authorization needed: {e.message}")
            return e.message 
        except Exception as e:
            logger.error(f"Error getting {url}: {e}")
            raise e

    
    def _post(self, url, data):
        try:
            headers = self._get_headers()
            response = httpx.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response
        except NotAuthorizedError as e:
            logger.warning(f"Reddit authorization needed: {e.message}")
            return e.message 
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return e.response.text or "Rate limit exceeded. Please try again later."
            else:
                raise e
        except Exception as e:
            logger.error(f"Error posting {url}: {e}")
            raise e

    def _put(self, url, data):
        try:
            headers = self._get_headers()
            response = httpx.put(url, headers=headers, json=data)
            response.raise_for_status()
            return response
        except NotAuthorizedError as e:
            logger.warning(f"Reddit authorization needed: {e.message}")
            return e.message 
        except Exception as e:
            logger.error(f"Error posting {url}: {e}")
            raise e

    def _delete(self, url):
        try:
            headers = self._get_headers()
            response = httpx.delete(url, headers=headers)
            response.raise_for_status()
            return response
        except NotAuthorizedError as e:
            logger.warning(f"Reddit authorization needed: {e.message}")
            return e.message 
        except Exception as e:
            logger.error(f"Error posting {url}: {e}")

    def validate(self):
        pass
    
    @abstractmethod
    def list_tools(self):
        pass