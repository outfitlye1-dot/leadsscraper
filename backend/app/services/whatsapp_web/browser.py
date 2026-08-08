"""Playwright persistent browser for WhatsApp Web (one shared session).

Sync Playwright is thread-affine (greenlet). ALL page/browser calls must run on
the dedicated Playwright thread via ``run()`` / ``call()``.

Preferred for WhatsApp Business: CDP attach to a real Chrome you open yourself
(``WA_WEB_CDP_URL``) so linking is not blocked as automation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import subprocess
import threading
import time
import urllib.request
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Callable, TypeVar

from app.core.config import BASE_DIR, get_settings

logger = logging.getLogger(__name__)

WHATSAPP_URL = "https://web.whatsapp.com/"
T = TypeVar("T")


class WhatsAppWebBrowser:
    """Long-lived Chromium / CDP Chrome session for WhatsApp Web."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._started = False
        self._cdp_mode = False
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._thread_needs_reset = False
        self._jobs: queue.Queue[tuple[Callable[[], Any], Future[Any]] | None] = queue.Queue()
        self._lock = threading.RLock()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def profile_dir(self) -> Path:
        settings = get_settings()
        path = Path(settings.WA_WEB_PROFILE_DIR)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def is_on_pw_thread(self) -> bool:
        return self._thread_id is not None and threading.get_ident() == self._thread_id

    def is_started(self) -> bool:
        return bool(self._started and self._page is not None)

    def is_cdp_mode(self) -> bool:
        return bool(self._cdp_mode)

    def call(self, fn: Callable[[], T], *, timeout: float = 180.0) -> T:
        self._ensure_worker()
        if self.is_on_pw_thread():
            return fn()
        fut: Future[T] = Future()
        self._jobs.put((fn, fut))
        return fut.result(timeout=timeout)

    def run(self, fn: Callable[[Any], T], *, timeout: float = 180.0) -> T:
        def _wrapped() -> T:
            page = self._ensure_started_unlocked()
            return fn(page)

        return self.call(_wrapped, timeout=timeout)

    def _ensure_worker(self) -> None:
        with self._lock:
            alive = bool(self._thread and self._thread.is_alive())
            if alive and not self._thread_needs_reset:
                return
            if alive and self._thread_needs_reset:
                try:
                    self._jobs.put(None)
                except Exception:
                    pass
                if self._thread:
                    self._thread.join(timeout=5)
            self._thread_needs_reset = False
            self._thread_id = None
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="wa-web-playwright",
                daemon=True,
            )
            self._thread.start()

    def _worker_loop(self) -> None:
        # After Playwright Sync starts, an asyncio loop stays running on this thread
        # (greenlet dispatcher). That is NORMAL — do not treat it as poison.
        self._thread_id = threading.get_ident()
        logger.info("WhatsApp Web Playwright thread started (id=%s)", self._thread_id)
        while True:
            item = self._jobs.get()
            if item is None:
                try:
                    self._shutdown_unlocked()
                finally:
                    self._thread_id = None
                break
            fn, fut = item
            try:
                fut.set_result(fn())
            except Exception as exc:
                fut.set_exception(exc)

    def _ensure_started_unlocked(self) -> Any:
        if self._started and self._page is not None:
            try:
                _ = self._page.url
                if self._cdp_mode:
                    bound = self._bind_whatsapp_page_unlocked()
                    if bound is not None:
                        return bound
                return self._page
            except Exception:
                logger.warning("WA Web page dead; restarting browser")
                self._shutdown_unlocked()

        # Failed previous start may leave Sync Playwright fiber running
        if self._playwright is not None and not self._started:
            self._shutdown_unlocked()

        settings = get_settings()
        if not settings.WA_WEB_ENABLED:
            raise RuntimeError("WhatsApp Web automation is disabled (WA_WEB_ENABLED=false)")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        try:
            self._playwright = sync_playwright().start()
            cdp = (settings.WA_WEB_CDP_URL or "").strip()
            if cdp:
                return self._start_cdp_unlocked(cdp)
            return self._start_launch_unlocked(settings)
        except Exception:
            # Must stop Sync Playwright or the next start() hits "inside asyncio loop"
            self._shutdown_unlocked()
            raise

    def _bind_whatsapp_page_unlocked(self) -> Any:
        """Prefer the live web.whatsapp.com tab across all CDP contexts."""
        contexts = []
        if self._browser is not None:
            try:
                contexts = list(self._browser.contexts)
            except Exception:
                contexts = []
        if self._context is not None and self._context not in contexts:
            contexts.insert(0, self._context)

        for ctx in contexts:
            try:
                pages = list(ctx.pages)
            except Exception:
                continue
            for page in pages:
                try:
                    if "web.whatsapp.com" in (page.url or ""):
                        self._context = ctx
                        self._page = page
                        return page
                except Exception:
                    continue
        return self._page

    def _start_cdp_unlocked(self, cdp_url: str) -> Any:
        logger.info("Connecting WhatsApp Web via CDP: %s", cdp_url)
        try:
            self._browser = self._playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as first_exc:
            logger.warning("CDP connect failed (%s) — launching Chrome automatically", first_exc)
            self._launch_cdp_chrome()
            if not self._wait_for_cdp(cdp_url, timeout_seconds=25.0):
                raise RuntimeError(
                    "Chrome debug port 9222 open nahi hua. Saari Chrome windows band karke "
                    "phir Connect dabao, ya manually: powershell -File scripts/launch_wa_chrome.ps1"
                ) from first_exc
            try:
                self._browser = self._playwright.chromium.connect_over_cdp(cdp_url)
            except Exception as exc:
                raise RuntimeError(
                    "Chrome start hua magar CDP connect fail. Dusri normal Chrome band rakho, "
                    f"sirf LeadGen wali Chrome chalne do. Detail: {exc}"
                ) from exc

        self._cdp_mode = True
        if self._browser.contexts:
            self._context = self._browser.contexts[0]
        else:
            self._context = self._browser.new_context()

        wa_page = self._bind_whatsapp_page_unlocked()
        if wa_page is None:
            wa_page = self._context.new_page()
            try:
                wa_page.goto(WHATSAPP_URL, wait_until="domcontentloaded", timeout=60_000)
            except Exception as exc:
                logger.warning("CDP navigate to WhatsApp: %s", exc)
            self._page = wa_page
        self._started = True
        return self._page

    def reattach_cdp(self) -> Any:
        """Drop stale Playwright CDP handle and connect again (Chrome stays open)."""
        settings = get_settings()
        cdp = (settings.WA_WEB_CDP_URL or "").strip()
        if not cdp:
            raise RuntimeError("WA_WEB_CDP_URL not configured")

        def _reattach() -> Any:
            was_cdp = self._cdp_mode
            # Disconnect Playwright only — do not kill the real Chrome profile.
            try:
                if self._browser is not None:
                    self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
            self._page = None
            self._started = False
            self._cdp_mode = False
            if self._playwright is not None and not was_cdp:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            if self._playwright is None:
                from playwright.sync_api import sync_playwright

                self._playwright = sync_playwright().start()
            return self._start_cdp_unlocked(cdp)

        return self.call(_reattach, timeout=90.0)

    def is_cdp_alive(self, timeout_seconds: float = 1.5) -> bool:
        """True when Chrome remote-debugging (WA_WEB_CDP_URL) is reachable."""
        settings = get_settings()
        cdp = (settings.WA_WEB_CDP_URL or "").strip()
        if not cdp:
            return False
        return self._wait_for_cdp(cdp, timeout_seconds=max(0.4, timeout_seconds))

    def _chrome_exe(self) -> Path | None:
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        for path in candidates:
            if path and path.is_file():
                return path
        return None

    def _cdp_profile_dir(self) -> Path:
        path = BASE_DIR / "data" / "wa_chrome_cdp"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _launch_cdp_chrome(self) -> None:
        chrome = self._chrome_exe()
        if chrome is None:
            raise RuntimeError("Google Chrome nahi mila — Chrome install karke dubara try karo")
        profile = self._cdp_profile_dir()
        args = [
            str(chrome),
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            WHATSAPP_URL,
        ]
        logger.info("Launching CDP Chrome profile=%s", profile)
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _wait_for_cdp(self, cdp_url: str, timeout_seconds: float = 25.0) -> bool:
        base = cdp_url.rstrip("/") + "/json/version"
        deadline = time.monotonic() + max(timeout_seconds, 5.0)
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(base, timeout=1.5) as resp:
                    if getattr(resp, "status", 200) == 200:
                        return True
            except Exception:
                time.sleep(0.4)
        return False

    def launch_cdp_chrome_public(self) -> dict[str, Any]:
        self._launch_cdp_chrome()
        settings = get_settings()
        cdp = (settings.WA_WEB_CDP_URL or "http://127.0.0.1:9222").strip()
        ready = self._wait_for_cdp(cdp, timeout_seconds=20.0)
        return {
            "ok": ready,
            "cdp_url": cdp,
            "message": (
                "Chrome khul gaya — is window mein WhatsApp Business link karo, phir Connect dabao"
                if ready
                else "Chrome start try hua — agar window na khuli to saari Chrome band karke dubara try karo"
            ),
        }

    def _start_launch_unlocked(self, settings: Any) -> Any:
        profile = self.profile_dir()
        use_chrome = bool(settings.WA_WEB_USE_CHROME)
        logger.info(
            "Starting WhatsApp Web browser (profile=%s headless=%s chrome=%s)",
            profile,
            settings.WA_WEB_HEADLESS,
            use_chrome,
        )
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(profile / "chromium"),
            "headless": bool(settings.WA_WEB_HEADLESS),
            "viewport": {"width": 1280, "height": 900},
            "locale": "en-US",
            "timezone_id": "Asia/Karachi",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            "ignore_default_args": ["--enable-automation"],
        }
        if use_chrome:
            launch_kwargs["channel"] = "chrome"
        else:
            launch_kwargs["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
        try:
            self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as exc:
            if use_chrome:
                logger.warning("Chrome channel failed (%s); falling back to Chromium", exc)
                launch_kwargs.pop("channel", None)
                launch_kwargs["user_agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
                self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            else:
                raise
        self._cdp_mode = False
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()
        try:
            self._page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
        except Exception:
            pass
        self._started = True
        return self._page

    def reset_profile(self) -> None:
        import shutil

        was_cdp = self._cdp_mode
        self.shutdown()
        if was_cdp:
            logger.info("CDP mode: skipped deleting Chrome profile")
            return
        profile = self.profile_dir() / "chromium"
        if profile.exists():
            shutil.rmtree(profile, ignore_errors=True)
            logger.info("WA Web profile cleared: %s", profile)

    def ensure_started(self) -> Any:
        return self.run(lambda page: page)

    def get_page(self) -> Any:
        return self.ensure_started()

    def goto_whatsapp(self, timeout_ms: int = 60_000) -> Any:
        def _go(page: Any) -> Any:
            try:
                if "web.whatsapp.com" not in (page.url or ""):
                    page.goto(WHATSAPP_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as exc:
                logger.warning("WA Web navigation issue: %s", exc)
            return page

        return self.run(_go, timeout=max(90.0, timeout_ms / 1000.0 + 15.0))

    def _shutdown_unlocked(self) -> None:
        try:
            if self._cdp_mode and self._browser is not None:
                self._browser.close()
            elif self._context is not None:
                self._context.close()
        except Exception as exc:
            logger.debug("WA Web context/browser close: %s", exc)
        try:
            if self._playwright is not None:
                self._playwright.stop()
        except Exception as exc:
            logger.debug("WA Web playwright stop: %s", exc)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._started = False
        self._cdp_mode = False

    def shutdown(self) -> None:
        with self._lock:
            alive = bool(self._thread and self._thread.is_alive())
        if not alive:
            self._shutdown_unlocked()
            return
        done: Future[None] = Future()

        def _stop() -> None:
            self._shutdown_unlocked()

        self._jobs.put((_stop, done))
        try:
            done.result(timeout=30)
        except Exception as exc:
            logger.debug("WA Web shutdown job: %s", exc)
        self._jobs.put(None)
        if self._thread:
            self._thread.join(timeout=10)
        self._thread = None
        self._thread_id = None
        self._thread_needs_reset = False
        logger.info("WhatsApp Web browser shut down")


wa_web_browser = WhatsAppWebBrowser()
