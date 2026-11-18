from abc import ABC, abstractmethod


class BaseConnector(ABC):

    def __init__(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Connector name is required.")

        self.name = name.strip().lower()

    @abstractmethod
    def get_supported_actions(self):
        pass

    @abstractmethod
    def execute(self, action, parameters, credentials=None):
        pass