class IntegrationRegistry:

    def __init__(self):
        self.integrations = {}

    def register(self, connector):

        if not hasattr(connector, "name"):
            raise ValueError("Invalid connector.")

        if not callable(getattr(connector, "execute", None)):
            raise ValueError("Connector must implement execute().")

        if not callable(getattr(connector, "get_supported_actions", None)):
            raise ValueError("Connector must implement get_supported_actions().")

        name = connector.name

        if name in self.integrations:
            raise ValueError("Integration already registered.")

        self.integrations[name] = connector

    def get(self, name):

        name = name.strip().lower()

        if name not in self.integrations:
            raise ValueError("Integration not found.")

        return self.integrations[name]

    def list_integrations(self):
        return list(self.integrations.keys())

    def has(self, name):
        return name.strip().lower() in self.integrations