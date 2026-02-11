import base64

import html2text
from anthropic import AsyncAnthropic
from loguru import logger
from playwright.async_api import async_playwright

from src.core.config import settings

PAGE_TIMEOUT = 30_000  # 30s


async def get_page_content(url: str) -> str:
    """Visit a URL with headless Chromium, return page content as Markdown."""
    logger.info(f"[tool] get_page_content: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
            html = await page.content()
            await browser.close()

        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.body_width = 0
        markdown = converter.handle(html)

        # Trim to avoid blowing up context
        if len(markdown) > 15_000:
            markdown = markdown[:15_000] + "\n\n...(truncated)"

        return markdown
    except Exception as e:
        return f"Failed to load page: {e}"


async def analyze_page_visual(url: str, query: str) -> str:
    """Take a screenshot of a URL, send it to the LLM for visual analysis."""
    logger.info(f"[tool] analyze_page_visual: {url} | query: {query[:80]}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            await page.goto(url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
            screenshot = await page.screenshot(full_page=False)
            await browser.close()

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
        return f"Visual analysis failed: {e}"
