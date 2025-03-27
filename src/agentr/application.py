from abc import ABC, abstractmethod
from agentr.integration import Integration
from agentr.exceptions import NotAuthorizedError
from loguru import logger
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
    
    def _handle_api_error(self, e, resource: str, operation: str):
        
        # Handle NotAuthorizedError first
        if isinstance(e, NotAuthorizedError):
            logger.warning(f"Authorization needed for {operation} {resource}: {e}")
            return {"error": str(e)} if isinstance(e, Exception) else str(e)
        
        # Handle HTTP Status Errors
        if isinstance(e, httpx.HTTPStatusError):
            status_code = e.response.status_code
            
            # Common HTTP error handling
            if status_code == 403:
                logger.error(f"Access denied for {operation} {resource}")
                return {"error": f"Error: Access denied to {resource}. It might be private or require specific permissions."}
            elif status_code == 404:
                logger.error(f"{resource.capitalize()} not found")
                return {"error": f"Error: {resource.capitalize()} not found."}
            else:
                logger.error(f"HTTP error during {operation} {resource}: {status_code} - {e.response.text}")
                return {"error": f"Error {operation} {resource}: Received status code {status_code}."}
        
        logger.exception(f"An unexpected error occurred while {operation} {resource}: {e}")
        return {"error": f"An unexpected error occurred while trying to {operation} {resource}."}
    
    def _get(self, url, params=None, headers=None):
        headers = headers or self._get_headers()
        try:
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response
        except (httpx.HTTPStatusError, NotAuthorizedError) as e:
            raise
    
    def _post(self, url, data=None, headers=None):
        headers = headers or self._get_headers()
        try:
            response = httpx.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response
        except (httpx.HTTPStatusError, NotAuthorizedError) as e:
            raise
    
    def _put(self, url, data=None, headers=None):
        headers = headers or self._get_headers()
        try:
            response = httpx.put(url, headers=headers, json=data)
            response.raise_for_status()
            return response
        except (httpx.HTTPStatusError, NotAuthorizedError) as e:
            raise
    
    def _delete(self, url, headers=None):
        headers = headers or self._get_headers()
        try:
            response = httpx.delete(url, headers=headers)
            response.raise_for_status()
            return response
        except (httpx.HTTPStatusError, NotAuthorizedError) as e:
            raise

    def validate(self):
        pass
    
    @abstractmethod
    def list_tools(self):
        pass