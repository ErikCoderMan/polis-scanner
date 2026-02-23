from collections import deque
from threading import Lock


class LogBuffer:
    def __init__(self, max_lines: int = 10_000):
        self.lines = deque(maxlen=max_lines)
        self.lock = Lock()

    def write(self, text: str):
        with self.lock:
            for line in text.rstrip().splitlines():
                self.lines.append(line)

    def get_text(self) -> str:
        with self.lock:
            return "\n".join(self.lines)

    def clear(self):
        with self.lock:
            self.lines.clear()

    # make objekt iterable
    def __iter__(self):
        with self.lock:
            return iter(list(self.lines))

    # make len(log_buffer) possible
    def __len__(self):
        return len(self.lines)
            
# global singleton
log_buffer = LogBuffer()
