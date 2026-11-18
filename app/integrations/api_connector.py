import json
from urllib.parse import urlencode, urlsplit, urlunsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from app.integrations.base_connector import BaseConnector


class _NoRedirectHandler(HTTPRedirectHandler):

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        raise HTTPError(
            request.full_url,
            code,
            "Redirects are not allowed for authenticated API requests.",
            headers,
            file_pointer
        )


class APIConnector(BaseConnector):

    ACTION_METHODS = {
        "read": "GET",
        "create": "POST",
        "update": "PATCH",
        "delete": "DELETE"
    }

    RESTRICTED_HEADERS = {
        "authorization",
        "proxy-authorization",
        "host",
        "cookie",
        "content-length",
        "connection"
    }

    def __init__(self, name, base_url, timeout=15):

        super().__init__(name)

        parsed = urlsplit(base_url)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("API must use a valid HTTPS base URL.")

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("A positive API timeout is required.")

        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.allowed_host = parsed.netloc.lower()

    def get_supported_actions(self):
        return list(self.ACTION_METHODS.keys())

    def _build_target(self, path, query):

        if not isinstance(path, str) or not path.strip():
            raise ValueError("API path is required.")

        supplied_path = urlsplit(path)

        if (
            supplied_path.scheme
            or supplied_path.netloc
            or supplied_path.query
            or supplied_path.fragment
            or path.startswith("//")
            or "\\\\" in path
            or "\\x00" in path
        ):
            raise ValueError("API path must be a relative path only.")

        decoded_path = unquote(supplied_path.path)

        if any(part == ".." for part in decoded_path.split("/")):
            raise ValueError("API path traversal is not allowed.")

        target = self.base_url + supplied_path.path.lstrip("/")
        parsed = urlsplit(target)

        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() != self.allowed_host
        ):
            raise ValueError("API destination is not allowed.")

        if not isinstance(query, dict):
            raise ValueError("Query parameters must be a dictionary.")

        return urlunsplit((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query, doseq=True),
            ""
        ))

    def execute(self, action, parameters, credentials=None):

        if action not in self.ACTION_METHODS:
            raise ValueError("Unsupported API action.")

        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary.")

        target = self._build_target(
            parameters.get("path"),
            parameters.get("query", {})
        )

        headers = parameters.get("headers", {})

        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary.")

        safe_headers = {}

        for key, value in headers.items():

            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Invalid API header.")

            normalized_key = key.strip().lower()

            if (
                not key
                or key != key.strip()
                or not key.isascii()
                or not key.replace("-", "").isalnum()
            ):
                raise ValueError("Invalid API header name.")

            if normalized_key in self.RESTRICTED_HEADERS:
                raise ValueError("Restricted API header.")

            safe_headers[key] = value

        if credentials is not None:

            if not isinstance(credentials, dict):
                raise ValueError("Invalid API credentials.")

            token = credentials.get("access_token")

            if token:
                safe_headers["Authorization"] = f"Bearer {token}"

        body = parameters.get("body")
        encoded_body = None

        if body is not None:
            encoded_body = json.dumps(body).encode("utf-8")
            safe_headers["Content-Type"] = "application/json"

        request = Request(
            target,
            data=encoded_body,
            headers=safe_headers,
            method=self.ACTION_METHODS[action]
        )

        opener = build_opener(_NoRedirectHandler)

        try:

            with opener.open(request, timeout=self.timeout) as response:

                response_text = response.read().decode(
                    "utf-8",
                    errors="replace"
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
                f"External API request failed with HTTP {error.code}. "
                "Redirects are not followed."
            ) from None

        except (URLError, TimeoutError):

            raise RuntimeError(
                "External API connection failed or timed out."
            ) from None
