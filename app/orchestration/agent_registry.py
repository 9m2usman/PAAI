class AgentRegistry:

    def __init__(self):
        self.agents = {}

    def register_agent(self, agent):
        name = getattr(agent, "name", None)

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Agent must have a valid name.")

        if not callable(getattr(agent, "run", None)):
            raise ValueError("Agent must implement run().")

        if name in self.agents:
            raise ValueError(f"Agent already registered: {name}")

        self.agents[name] = agent

    def get_agent(self, name):
        agent = self.agents.get(name)

        if agent is None:
            raise ValueError(f"Agent not registered: {name}")

        return agent

    def list_agents(self):
        return list(self.agents.keys())

    def has_agent(self, name):
        return name in self.agents