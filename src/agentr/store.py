
from abc import ABC, abstractmethod


class Store(ABC):
    @abstractmethod
    def get(self, key: str):
        pass

    @abstractmethod
    def set(self, key: str, value: str):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

class MemoryStore:
    """
    Acts as credential store for the applications.
    Responsible for storing and retrieving credentials. 
    Ideally should be a key value store
    """
    def __init__(self):
        self.data = {}

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: str):
        self.data[key] = value

    def delete(self, key: str):
        del self.data[key]

