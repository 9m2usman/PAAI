from urllib.parse import urlsplit

from app.integrations.base_connector import BaseConnector


class BrowserConnector(BaseConnector):

    def __init__(self, browser_driver, allowed_domains):

        super().__init__("browser")

        if browser_driver is None:
            raise ValueError("Browser driver is required.")

        if not isinstance(allowed_domains, list) or not allowed_domains:
            raise ValueError("Allowed domains are required.")

        self.browser_driver = browser_driver
        self.allowed_domains = {
            domain.strip().lower().lstrip(".")
            for domain in allowed_domains
            if isinstance(domain, str) and domain.strip()
        }

        if not self.allowed_domains:
            raise ValueError("Valid allowed domains are required.")

        if hasattr(browser_driver, "set_allowed_domains"):
            browser_driver.set_allowed_domains(self.allowed_domains)

    def get_supported_actions(self):

        return [
            "open_page",
            "extract_text",
            "click",
            "fill"
        ]

    def _validate_url(self, url):

        if not isinstance(url, str):
            raise ValueError("Valid URL is required.")

        parsed = urlsplit(url)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Browser only supports safe HTTPS URLs.")

        hostname = parsed.hostname.lower()

        allowed = any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in self.allowed_domains
        )

        if not allowed:
            raise PermissionError("Website domain is not allowed.")

        return url

    def execute(self, action, parameters, credentials=None):

        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary.")

        if action == "open_page":

            url = self._validate_url(parameters.get("url"))
            result = self.browser_driver.open_page(url)

            final_url = result.get("url") if isinstance(result, dict) else None
            self._validate_url(final_url)

            return result

        if action == "extract_text":
            return self.browser_driver.extract_text()

        if action == "click":

            selector = parameters.get("selector")

            if not isinstance(selector, str) or not selector.strip():
                raise ValueError("Element selector is required.")

            result = self.browser_driver.click(selector)

            current_url = self.browser_driver.current_url()
            self._validate_url(current_url)

            return result

        if action == "fill":

            selector = parameters.get("selector")
            value = parameters.get("value")

            if not isinstance(selector, str) or not selector.strip():
                raise ValueError("Element selector is required.")

            if not isinstance(value, str):
                raise ValueError("Input value must be text.")

            self._validate_url(self.browser_driver.current_url())

            return self.browser_driver.fill(selector, value)

        raise ValueError("Unsupported browser action.")
