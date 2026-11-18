class PlaywrightDriver:

    def __init__(self, headless=True):

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Install it before using the browser."
            ) from None

        self.playwright_manager = sync_playwright()
        self.playwright = self.playwright_manager.start()
        self.browser = self.playwright.chromium.launch(
            headless=headless
        )
        self.page = self.browser.new_page()

    def open_page(self, url):

        response = self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        return {
            "url": self.page.url,
            "status": response.status if response else None,
            "title": self.page.title()
        }

    def extract_text(self):

        return self.page.locator("body").inner_text()

    def click(self, selector):

        self.page.locator(selector).click(timeout=10000)

        return {"status": "clicked", "selector": selector}

    def fill(self, selector, value):

        self.page.locator(selector).fill(
            value,
            timeout=10000
        )

        return {"status": "filled", "selector": selector}

    def close(self):

        self.browser.close()
        self.playwright_manager.stop()