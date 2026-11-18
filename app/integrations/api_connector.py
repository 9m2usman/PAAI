import json
from urllib.parse import urljoin, urlsplit, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from app.integrations.base_connector import BaseConnector


class APIConnector(BaseConnector):

    ACTION_METHODS = {
        "read": "GET",
        "create": "POST",
        "update": "PATCH",
        "delete": "DELETE"
    }

    def __init__(self, name, base_url, timeout=15):

        super().__init__(name)

        parsed = urlsplit(base_url)

        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("API must use a valid HTTPS base URL.")

        if parsed.username or parsed.password:
            raise ValueError("Credentials must not be included in the URL.")

        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.allowed_host = parsed.netloc.lower()

    def get_supported_actions(self):
        return list(self.ACTION_METHODS.keys())

    def execute(self, action, parameters, credentials=None):

        if action not in self.ACTION_METHODS:
            raise ValueError("Unsupported API action.")

        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary.")

        path = parameters.get("path")

        if not isinstance(path, str) or not path.strip():
            raise ValueError("API path is required.")

        if path.startswith("//"):
            raise ValueError("Invalid API path.")

        target = urljoin(self.base_url, path.lstrip("/"))
        parsed = urlsplit(target)

        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() != self.allowed_host
            or any(part == ".." for part in parsed.path.split("/"))
        ):
            raise ValueError("API destination is not allowed.")

        query = parameters.get("query", {})

        if not isinstance(query, dict):
            raise ValueError("Query parameters must be a dictionary.")

        if query:
            separator = "&" if parsed.query else "?"
            target += separator + urlencode(query, doseq=True)

        headers = parameters.get("headers", {})

        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary.")

        safe_headers = {}

        for key, value in headers.items():

            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Invalid API header.")

            if key.lower() in {
                "authorization",
                "host",
                "cookie",
                "content-length"
            }:
                raise ValueError("Restricted API header.")

            safe_headers[key] = value

        if credentials:

            token = credentials.get("access_token")

            if token:
                safe_headers["Authorization"] = f"Bearer {token}"

        body = parameters.get("body")
        encoded_body = None

        if body is not None:

            encoded_body = json.dumps(body).encode("utf-8")
            safe_headers["Content-Type"] = "application/json"

        method = self.ACTION_METHODS[action]

        request = Request(
            target,
            data=encoded_body,
            headers=safe_headers,
            method=method
        )

        try:

            with urlopen(request, timeout=self.timeout) as response:

                response_text = response.read().decode(
                    "utf-8", errors="replace"
                )

                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    response_data = response_text

                return {
                    "status_code": response.status,
                    "data": response_data
                }

        except HTTPError as error:

            raise RuntimeError(
                f"External API returned HTTP {error.code}."
            ) from None

        except (URLError, TimeoutError):

            raise RuntimeError(
                "External API connection failed or timed out."
            ) from None