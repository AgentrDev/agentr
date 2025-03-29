from abc import ABC, abstractmethod
import os

from loguru import logger
from agentr.exceptions import NotAuthorizedError
from agentr.store import Store
import httpx




class Integration(ABC):
    """Abstract base class for handling application integrations and authentication.
    
    This class defines the interface for different types of integrations that handle
    authentication and authorization with external services.
    
    Args:
        name: The name identifier for this integration
        store: Optional Store instance for persisting credentials and other data
    
    Attributes:
        name: The name identifier for this integration
        store: Store instance for persisting credentials and other data
    """
    def __init__(self, name: str, store: Store = None):
        self.name = name
        self.store = store

    @abstractmethod
    def authorize(self):
        """Authorize the integration.
        
        Returns:
            str: Authorization URL.
        """
        pass
    
    @abstractmethod
    def get_credentials(self):
        """Get credentials for the integration.
        
        Returns:
            dict: Credentials for the integration.
        
        Raises:
            NotAuthorizedError: If credentials are not found.
        """
        pass

    @abstractmethod
    def set_credentials(self, credentials: dict):
        """Set credentials for the integration.
        
        Args:
            credentials: Credentials for the integration.
        """
        pass


