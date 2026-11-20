"""Shared Playwright helper for live scrapers.

Each airline gets its own persistent, visible Chromium profile under
data/browser-profiles/<code>, so cookies and anti-bot tokens survive between runs.
A visible (non-headless) browser on your home connection is flagged far less often.
"""
from __future__ import annotations

from typing import Any

from .. import config


class BrowserSession:
    def __init__(self, code: str, headless: bool = False):
        self.code = code
        self.headless = headless
        self._pw = None
        self._ctx = None

    async def page(self):
        if self._ctx is None:
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise RuntimeError(
                    "Live scrapers need Playwright: "
                    "pip install -r requirements-live.txt && playwright install chromium"
                ) from exc
            profile = config.BROWSER_PROFILE_DIR / self.code
            profile.mkdir(parents=True, exist_ok=True)
            self._pw = await async_playwright().start()
            self._ctx = await self._pw.chromium.launch_persistent_context(
                str(profile), headless=self.headless, viewport={"width": 1366, "height": 900}
            )
        return self._ctx.pages[0] if self._ctx.pages else await self._ctx.new_page()

    async def capture_json(self, url: str, match: str, timeout_ms: int = 45_000) -> Any:
        """Open `url` and return the JSON body of the first response whose URL contains `match`.

        This is the main pattern for airline sites: load the normal search page and
        read the JSON its own front end requests, instead of parsing HTML.
        """
        page = await self.page()
        async with page.expect_response(
            lambda r: match in r.url and r.ok, timeout=timeout_ms
        ) as info:
            await page.goto(url, wait_until="domcontentloaded")
        response = await info.value
        return await response.json()

    async def close(self) -> None:
        if self._ctx is not None:
            await self._ctx.close()
            self._ctx = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None
