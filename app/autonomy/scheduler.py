class AutonomyScheduler:
    """One polling tick; process supervision and cadence belong to the host worker."""
    def __init__(self, engine):
        self.engine = engine

    def run_due_once(self):
        return self.engine.run_due_once()
