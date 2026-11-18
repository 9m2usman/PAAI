import base64
from email.message import EmailMessage
from urllib.parse import quote

from app.integrations.base_connector import BaseConnector
from app.integrations.api_connector import APIConnector


class GmailConnector(BaseConnector):

    def __init__(self):
        super().__init__("gmail")

        self.api = APIConnector(
            name="gmail_api",
            base_url="https://gmail.googleapis.com"
        )

    def get_supported_actions(self):

        return [
            "list_emails",
            "read_email",
            "create_draft",
            "send_email"
        ]

    def _encode_email(self, parameters):

        required = {"to", "subject", "body"}

        if not required.issubset(parameters):
            raise ValueError("Email requires recipient, subject and body.")

        for field in required:
            if not isinstance(parameters[field], str):
                raise ValueError("Email fields must be text.")

        message = EmailMessage()
        message["To"] = parameters["to"]
        message["Subject"] = parameters["subject"]
        message.set_content(parameters["body"])

        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        return raw_message

    def execute(self, action, parameters, credentials=None):

        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary.")

        if not credentials or not credentials.get("access_token"):
            raise PermissionError("Gmail OAuth credentials are required.")

        if action == "list_emails":

            max_results = parameters.get("max_results", 10)

            if not isinstance(max_results, int) or not 1 <= max_results <= 100:
                raise ValueError("max_results must be an integer from 1 to 100.")

            query = parameters.get("query", "")

            if not isinstance(query, str):
                raise ValueError("Gmail query must be text.")

            return self.api.execute(
                "read",
                {
                    "path": "gmail/v1/users/me/messages",
                    "query": {
                        "maxResults": max_results,
                        "q": query
                    }
                },
                credentials
            )

        if action == "read_email":

            message_id = parameters.get("message_id")

            if not isinstance(message_id, str) or not message_id.strip():
                raise ValueError("Message ID is required.")

            return self.api.execute(
                "read",
                {
                    "path": (
                        "gmail/v1/users/me/messages/"
                        + quote(message_id, safe="")
                    ),
                    "query": {"format": "full"}
                },
                credentials
            )

        if action in {"create_draft", "send_email"}:

            raw_message = self._encode_email(parameters)

            if action == "create_draft":

                path = "gmail/v1/users/me/drafts"
                body = {"message": {"raw": raw_message}}

            else:

                path = "gmail/v1/users/me/messages/send"
                body = {"raw": raw_message}

            return self.api.execute(
                "create",
                {
                    "path": path,
                    "body": body
                },
                credentials
            )

        raise ValueError("Unsupported Gmail action.")
