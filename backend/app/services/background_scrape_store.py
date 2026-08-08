"""In-memory state for silent per-user background scraping while logged in."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

HEARTBEAT_TTL_SECONDS = 300
BACKGROUND_ROUND_SECONDS = 120
MAX_BACKGROUND_LOGS = 250


@dataclass
class BackgroundScrapeState:
    user_id: int
    running: bool = False
    last_heartbeat: float = field(default_factory=time.time)
    total_saved: int = 0
    last_query: str = ""
    iteration: int = 0
    progress: int = 0
    stage: str = "idle"
    message: str = "Waiting to start..."
    logs: list[dict] = field(default_factory=list)
    log_seq: int = 0


class BackgroundScrapeStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[int, BackgroundScrapeState] = {}
        self._stop_flags: dict[int, threading.Event] = {}
        self._threads: dict[int, threading.Thread] = {}

    def touch_heartbeat(self, user_id: int) -> BackgroundScrapeState:
        with self._lock:
            state = self._state.setdefault(user_id, BackgroundScrapeState(user_id=user_id))
            state.last_heartbeat = time.time()
            return state

    def is_session_alive(self, user_id: int) -> bool:
        with self._lock:
            state = self._state.get(user_id)
            if not state:
                return False
            return (time.time() - state.last_heartbeat) <= HEARTBEAT_TTL_SECONDS

    def mark_running(self, user_id: int) -> None:
        with self._lock:
            state = self._state.setdefault(user_id, BackgroundScrapeState(user_id=user_id))
            state.running = True

    def mark_stopped(self, user_id: int) -> None:
        with self._lock:
            state = self._state.get(user_id)
            if state:
                state.running = False

    def record_round(self, user_id: int, *, saved: int, query_label: str) -> None:
        with self._lock:
            state = self._state.setdefault(user_id, BackgroundScrapeState(user_id=user_id))
            state.iteration += 1
            state.total_saved += saved
            state.last_query = query_label

    def append_log(
        self,
        user_id: int,
        text: str,
        *,
        level: str = "info",
        stage: str = "",
    ) -> None:
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            state = self._state.setdefault(user_id, BackgroundScrapeState(user_id=user_id))
            if state.logs and state.logs[-1].get("text") == text:
                return
            state.log_seq += 1
            state.logs.append(
                {
                    "seq": state.log_seq,
                    "ts": datetime.now(UTC).isoformat(),
                    "level": level,
                    "stage": stage or state.stage,
                    "text": text,
                }
            )
            if len(state.logs) > MAX_BACKGROUND_LOGS:
                state.logs = state.logs[-MAX_BACKGROUND_LOGS:]

    def update_progress(
        self,
        user_id: int,
        progress: int,
        stage: str,
        message: str,
    ) -> None:
        with self._lock:
            state = self._state.setdefault(user_id, BackgroundScrapeState(user_id=user_id))
            state.progress = max(0, min(100, progress))
            state.stage = stage
            state.message = message

    def get_status(self, user_id: int) -> dict:
        with self._lock:
            state = self._state.get(user_id)
            if not state:
                return {
                    "active": False,
                    "running": False,
                    "total_saved": 0,
                    "iteration": 0,
                    "last_query": "",
                    "progress": 0,
                    "stage": "idle",
                    "message": "Not started",
                    "logs": [],
                }
            alive = (time.time() - state.last_heartbeat) <= HEARTBEAT_TTL_SECONDS
            return {
                "active": alive,
                "running": state.running and alive,
                "total_saved": state.total_saved,
                "iteration": state.iteration,
                "last_query": state.last_query,
                "progress": state.progress,
                "stage": state.stage,
                "message": state.message,
                "logs": list(state.logs),
            }

    def get_stop_event(self, user_id: int) -> threading.Event:
        with self._lock:
            if user_id not in self._stop_flags:
                self._stop_flags[user_id] = threading.Event()
            return self._stop_flags[user_id]

    def set_thread(self, user_id: int, thread: threading.Thread) -> None:
        with self._lock:
            self._threads[user_id] = thread

    def is_worker_alive(self, user_id: int) -> bool:
        with self._lock:
            thread = self._threads.get(user_id)
            return thread is not None and thread.is_alive()

    def start_worker_if_dead(self, user_id: int, factory) -> bool:
        """Atomically start a worker thread when none is alive."""
        with self._lock:
            thread = self._threads.get(user_id)
            if thread is not None and thread.is_alive():
                return False
            if user_id not in self._stop_flags:
                self._stop_flags[user_id] = threading.Event()
            stop_event = self._stop_flags[user_id]
            stop_event.clear()
            thread = factory(stop_event)
            self._threads[user_id] = thread
            thread.start()
            return True

    def clear_thread(self, user_id: int) -> None:
        with self._lock:
            thread = self._threads.get(user_id)
            if thread is not None and thread.is_alive():
                return
            self._threads.pop(user_id, None)

    def stop_worker(self, user_id: int) -> None:
        with self._lock:
            event = self._stop_flags.get(user_id)
            if event:
                event.set()
            # Keep thread reference until it exits — prevents start_worker_if_dead
            # from spawning a second worker while the old one finishes a round.
            state = self._state.get(user_id)
            if state:
                state.running = False


background_scrape_store = BackgroundScrapeStore()
