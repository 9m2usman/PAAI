import logging
import signal
import threading
from app.identity.context import identity_scope

logger = logging.getLogger(__name__)

class AutonomyWorker:
    def __init__(self, runtime, poll_interval_seconds=5):
        if poll_interval_seconds < 1:
            raise ValueError("Worker polling interval must be at least one second.")
        self.runtime = runtime
        self.poll_interval_seconds = poll_interval_seconds
        self.stop_event = threading.Event()

    def stop(self, *_):
        self.stop_event.set()

    def run_once(self):
        identities = self.runtime.auth_repository.list_principals()
        results = []
        for principal in identities:
            if self.stop_event.is_set():
                break
            try:
                with identity_scope(principal):
                    results.extend(self.runtime.scheduler.run_due_once())
            except Exception:
                logger.exception("Autonomy worker tick failed for one tenant.")
        return results

    def run_forever(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Autonomy worker polling cycle failed.")
            self.stop_event.wait(self.poll_interval_seconds)
