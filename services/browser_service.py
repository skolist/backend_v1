import asyncio
import logging
from collections.abc import Callable
from typing import Any

from playwright.async_api import Browser, Playwright, async_playwright

logger = logging.getLogger(__name__)


class BrowserService:
    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Initialize the browser and the worker loop."""
        if self._running:
            return

        logger.info("Starting BrowserService...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("BrowserService started.")

    async def stop(self):
        """Stop the worker loop and close the browser."""
        if not self._running:
            return

        logger.info("Stopping BrowserService...")
        self._running = False
        await self._queue.put(None)  # Sentinel to stop worker

        if self._worker_task:
            await self._worker_task

        if self._browser:
            await self._browser.close()

        if self._playwright:
            await self._playwright.stop()

        logger.info("BrowserService stopped.")

    async def _worker(self):
        """Background worker to process browser tasks sequentially."""
        logger.info("BrowserService worker loop started.")
        while True:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break

            func, context_options, args, kwargs, future = item

            try:
                if not self._browser:
                    raise RuntimeError("Browser is not initialized")

                # Create a new context/page for each task to ensure isolation
                context = await self._browser.new_context(**(context_options or {}))
                page = await context.new_page()

                try:
                    # Pass the page as the first argument to the function
                    result = await func(page, *args, **kwargs)
                    if not future.done():
                        future.set_result(result)
                except Exception as e:
                    logger.exception(f"Error executing browser task: {e}")
                    if not future.done():
                        future.set_exception(e)
                finally:
                    await page.close()
                    await context.close()

            except Exception as e:
                logger.critical(f"Critical error in browser worker: {e}")
                if not future.done():
                    future.set_exception(e)
            finally:
                self._queue.task_done()
        logger.info("BrowserService worker loop exited.")

    async def _submit(self, func: Callable, context_options: dict[str, Any], *args, **kwargs) -> Any:
        """Submit a task to the queue and wait for the result."""
        if not self._running:
            raise RuntimeError("BrowserService is not running")

        future = asyncio.get_running_loop().create_future()
        await self._queue.put((func, context_options, args, kwargs, future))
        return await future

    async def generate_pdf(self, html_content: str, pdf_options: dict[str, Any] = None) -> bytes:
        """
        Generate a PDF from HTML content.
        """

        async def _task(page, html, options):
            await page.set_content(html, wait_until="networkidle")
            return await page.pdf(**(options or {}))

        return await self._submit(_task, None, html_content, pdf_options)

    async def take_screenshot(
        self,
        html_content: str,
        selector: str = "body",
        screenshot_options: dict[str, Any] = None,
        context_options: dict[str, Any] = None,
    ) -> bytes:
        """
        Take a screenshot of a specific element from HTML content.
        """

        async def _task(page, html, sel, options):
            await page.set_content(html, wait_until="networkidle")
            element = await page.query_selector(sel)
            if not element:
                logger.warning(f"Selector '{sel}' not found, falling back to body")
                element = await page.query_selector("body")

            return await element.screenshot(**(options or {}))

        return await self._submit(_task, context_options, html_content, selector, screenshot_options)

    # We need to handle context options (like viewport, scale factor)
    # Let's enhance _submit to accept context_options

    async def _submit_with_options(self, func: Callable, context_options: dict[str, Any], *args, **kwargs) -> Any:
        # We need a new internal message type or just change the signature
        pass
