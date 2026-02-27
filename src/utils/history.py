from collections import deque
from threading import Lock
from src.core.config import settings

class CommandHistory:
    def __init__(self, capacity: int = 0):
        if not capacity:
            capacity = settings.command_history_len or 1000
        
        self._history = deque(maxlen=capacity)
        self._lock = Lock()
        self._cursor = 0

    def append(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            return

        with self._lock:
            # Avoid duplicate consecutive commands
            if self._history and self._history[0] == clean:
                return

            self._history.appendleft(clean)
            self._cursor = -1

    # Navigation

    def previous(self) -> str | None:
        """Navigate older history"""
        with self._lock:
            if not self._history:
                return None

            self._cursor = min(self._cursor + 1, len(self._history) - 1)
            return self._history[self._cursor]

    def next(self) -> str | None:
        """Navigate newer history"""
        with self._lock:
            if not self._history:
                return None

            self._cursor = max(self._cursor - 1, -1)

            if self._cursor == -1:
                return ""

            return self._history[self._cursor]

    def reset_cursor(self):
        with self._lock:
            self._cursor = -1
