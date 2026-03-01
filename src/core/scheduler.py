import asyncio
from typing import Coroutine

class Scheduler:
    def __init__(self):
        self._workers: dict[str, asyncio.Task] = {}
    
    def running_tasks(self) -> list[asyncio.Task]:
        return [t for t in self._workers.values() if not t.done()]

    def spawn(self, name: str, coro: Coroutine):
        if name in self._workers:
            raise RuntimeError(f"Worker '{name}' already running")

        task = asyncio.create_task(coro)
        self._workers[name] = task

        def _cleanup(_):
            self._workers.pop(name, None)

        task.add_done_callback(_cleanup)
        return task

    def has_worker(self, name: str) -> bool:
        task = self._workers.get(name)
        return task is not None and not task.done()

    def stop_worker(self, name: str):
        task = self._workers.get(name)
        if task and not task.done():
            task.cancel()

    async def stop_and_wait(self, name: str, timeout: float | None = None):
        task = self._workers.get(name)
        if not task:
            return

        if not task.done():
            task.cancel()

        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            pass
