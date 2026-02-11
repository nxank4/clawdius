import base64

import html2text
from anthropic import AsyncAnthropic
from loguru import logger
from playwright.async_api import Browser, Playwright, async_playwright

from src.core.config import settings

PAGE_TIMEOUT = 30_000  # 30s


class BrowserManager:
    """Manages a shared headless Chromium instance across tool calls."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def _ensure_browser(self) -> Browser:
        if self._browser and self._browser.is_connected():
            return self._browser
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        logger.info("[browser] Launched headless Chromium")
        return self._browser

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def web_search(self, query: str) -> str:
        """Navigate to DuckDuckGo, search, and scrape top results."""
        logger.info(f"[tool] web_search: {query}")
        try:
            browser = await self._ensure_browser()
            page = await browser.new_page()
            try:
                await page.goto(
                    "https://duckduckgo.com/",
                    timeout=PAGE_TIMEOUT,
                    wait_until="domcontentloaded",
                )

                # Type query and search
                search_box = page.locator('input[name="q"]')
                await search_box.fill(query)
                await search_box.press("Enter")

                # Wait for results to appear
                await page.wait_for_selector(
                    "[data-result], .result, article[data-testid='result']",
                    timeout=PAGE_TIMEOUT,
                )
                # Give results a moment to fully render
                await page.wait_for_timeout(2000)

                # Scrape results from the DOM
                results = await page.evaluate("""() => {
                    const items = [];
                    // Try multiple selectors for DuckDuckGo result elements
                    const selectors = [
                        'article[data-testid="result"]',
                        'div.result',
                        'div[data-result]',
                        'li[data-layout="organic"]',
                    ];
                    let elements = [];
                    for (const sel of selectors) {
                        elements = document.querySelectorAll(sel);
                        if (elements.length > 0) break;
                    }
                    for (const el of Array.from(elements).slice(0, 5)) {
                        const a = el.querySelector('a[href]');
                        const title = (
                            el.querySelector('h2') ||
                            el.querySelector('a[data-testid="result-title-a"]') ||
                            el.querySelector('.result__a') ||
                            a
                        );
                        const snippet = (
                            el.querySelector('[data-result="snippet"]') ||
                            el.querySelector('span[data-testid="result-snippet"]') ||
                            el.querySelector('.result__snippet') ||
                            el.querySelector('p')
                        );
                        if (a) {
                            items.push({
                                title: title ? title.innerText.trim() : '',
                                href: a.href || '',
                                snippet: snippet ? snippet.innerText.trim() : '',
                            });
                        }
                    }
                    return items;
                }""")

                if not results:
                    return "No search results found."

                lines = []
                for r in results:
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    href = r.get("href", "")
                    lines.append(f"**{title}**\n{snippet}\n{href}")
                return "\n\n".join(lines)

            finally:
                await page.close()

        except Exception as e:
            logger.error(f"[tool] web_search failed: {e}")
            return f"Search failed: {e}"

    async def read_webpage(self, url: str) -> str:
        """Load a URL and return its content as Markdown."""
        logger.info(f"[tool] read_webpage: {url}")
        try:
            browser = await self._ensure_browser()
            page = await browser.new_page()
            try:
                await page.goto(
                    url,
                    timeout=PAGE_TIMEOUT,
                    wait_until="domcontentloaded",
                )
                html = await page.content()
            finally:
                await page.close()

            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = True
            converter.body_width = 0
            markdown = converter.handle(html)

            # Trim to ~4000 tokens (roughly 16000 chars)
            if len(markdown) > 16_000:
                markdown = markdown[:16_000] + "\n\n...(truncated)"

            return markdown

        except Exception as e:
            logger.error(f"[tool] read_webpage failed: {e}")
            return f"Failed to load page: {e}"

    async def analyze_page_visual(self, url: str, query: str) -> str:
        """Take a screenshot and send it to the LLM for visual analysis."""
        logger.info(f"[tool] analyze_page_visual: {url} | query: {query[:80]}")
        try:
            browser = await self._ensure_browser()
            page = await browser.new_page(
                viewport={"width": 1280, "height": 900},
            )
            try:
                await page.goto(
                    url,
                    timeout=PAGE_TIMEOUT,
                    wait_until="domcontentloaded",
                )
                screenshot = await page.screenshot(full_page=False)
            finally:
                await page.close()

            img_b64 = base64.standard_b64encode(screenshot).decode()

            client = AsyncAnthropic(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
            )
            response = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this screenshot of {url}. {query}",
                        },
                    ],
                }],
            )
            return response.content[0].text if response.content else "(no analysis)"

        except Exception as e:
            logger.error(f"[tool] analyze_page_visual failed: {e}")
            return f"Visual analysis failed: {e}"


# Shared singleton instance
browser_manager = BrowserManager()
