from urllib.parse import urlsplit


class PlaywrightDriver:

    def __init__(self, headless=True, allowed_domains=None):

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Install it before using the browser."
            ) from None

        self.allowed_domains = set()
        self.playwright_manager = sync_playwright()
        self.playwright = self.playwright_manager.start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        if allowed_domains:
            self.set_allowed_domains(allowed_domains)

    def set_allowed_domains(self, allowed_domains):

        self.allowed_domains = {
            domain.strip().lower().lstrip(".")
            for domain in allowed_domains
        }

        if not self.allowed_domains:
            raise ValueError("At least one allowed browser domain is required.")

        self.page.unroute("**/*")
        self.page.route("**/*", self._guard_request)

    def _is_allowed_url(self, url):

        try:
            parsed = urlsplit(url)

            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.port not in (None, 443)
                or parsed.username
                or parsed.password
            ):
                return False

            hostname = parsed.hostname.lower()

            return any(
                hostname == domain or hostname.endswith("." + domain)
                for domain in self.allowed_domains
            )

        except (TypeError, ValueError):
            return False

    def _guard_request(self, route):

        if self._is_allowed_url(route.request.url):
            route.continue_()
        else:
            route.abort("blockedbyclient")

    def open_page(self, url):

        if not self._is_allowed_url(url):
            raise PermissionError("Browser destination is not allowed.")

        response = self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        if not self._is_allowed_url(self.page.url):
            self.page.goto("about:blank")
            raise PermissionError("Browser navigation left the allowed domains.")

        return {
            "url": self.page.url,
            "status": response.status if response else None,
            "title": self.page.title()
        }

    def current_url(self):
        return self.page.url

    def extract_text(self):

        if not self._is_allowed_url(self.page.url):
            raise PermissionError("Current browser page is not allowed.")

        return self.page.locator("body").inner_text()

    def click(self, selector):

        if not self._is_allowed_url(self.page.url):
            raise PermissionError("Current browser page is not allowed.")

        self.page.locator(selector).click(timeout=10000)

        if not self._is_allowed_url(self.page.url):
            self.page.goto("about:blank")
            raise PermissionError("Browser navigation left the allowed domains.")

        return {"status": "clicked", "selector": selector}

    def fill(self, selector, value):

        if not self._is_allowed_url(self.page.url):
            raise PermissionError("Current browser page is not allowed.")

        self.page.locator(selector).fill(
            value,
            timeout=10000
        )

        return {"status": "filled", "selector": selector}

    def close(self):

        try:
            self.context.close()
            self.browser.close()
        finally:
            self.playwright_manager.stop()
