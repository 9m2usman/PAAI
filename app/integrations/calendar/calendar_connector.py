from urllib.parse import quote

from app.integrations.base_connector import BaseConnector
from app.integrations.api_connector import APIConnector


class CalendarConnector(BaseConnector):

    def __init__(self):
        super().__init__("calendar")

        self.api = APIConnector(
            name="calendar_api",
            base_url="https://www.googleapis.com"
        )

    def get_supported_actions(self):

        return [
            "list_events",
            "create_event",
            "update_event",
            "delete_event"
        ]

    def execute(self, action, parameters, credentials=None):

        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary.")

        if not credentials or not credentials.get("access_token"):
            raise PermissionError(
                "Calendar OAuth credentials are required."
            )

        base_path = "calendar/v3/calendars/primary/events"

        if action == "list_events":

            return self.api.execute(
                "read",
                {
                    "path": base_path,
                    "query": {
                        "maxResults": parameters.get("max_results", 10),
                        "timeMin": parameters.get("time_min", ""),
                        "timeMax": parameters.get("time_max", "")
                    }
                },
                credentials
            )

        if action == "create_event":

            event = parameters.get("event")

            if not isinstance(event, dict):
                raise ValueError("Calendar event data is required.")

            if "summary" not in event or "start" not in event or "end" not in event:
                raise ValueError("Event requires summary, start and end.")

            return self.api.execute(
                "create",
                {
                    "path": base_path,
                    "body": event
                },
                credentials
            )

        if action in {"update_event", "delete_event"}:

            event_id = parameters.get("event_id")

            if not isinstance(event_id, str) or not event_id.strip():
                raise ValueError("Event ID is required.")

            path = base_path + "/" + quote(event_id, safe="")

            if action == "update_event":

                event = parameters.get("event")

                if not isinstance(event, dict) or not event:
                    raise ValueError("Updated event data is required.")

                return self.api.execute(
                    "update",
                    {
                        "path": path,
                        "body": event
                    },
                    credentials
                )

            return self.api.execute(
                "delete",
                {"path": path},
                credentials
            )

        raise ValueError("Unsupported Calendar action.")