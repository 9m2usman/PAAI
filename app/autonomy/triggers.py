import json
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class AutonomyEvent:
    event_type: str
    payload: dict
    occurred_at: str

class TriggerRegistry:
    def __init__(self, allowed_event_types=None, max_payload_bytes=16384):
        self.allowed_event_types = set(allowed_event_types or {"report.ready", "document.uploaded", "calendar.updated"})
        self.max_payload_bytes = max_payload_bytes

    def validate_event(self, event_type, payload):
        if event_type not in self.allowed_event_types:
            raise ValueError("Event type is not registered.")
        if not isinstance(payload, dict):
            raise ValueError("Event payload must be an object.")
        try:
            size = len(json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"))
        except Exception:
            raise ValueError("Event payload is not serializable.") from None
        if size > self.max_payload_bytes:
            raise ValueError("Event payload exceeds the configured limit.")
        return AutonomyEvent(event_type, payload, datetime.now(timezone.utc).isoformat())
