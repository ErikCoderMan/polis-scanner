import tkinter as tk
import asyncio
import threading
from src.core.logger import get_logger
from src.core.config import settings
from .ui import GUIApp

logger = get_logger(__name__)


def run_gui() -> int:
    logger.info("Starting GUI")
    logger.info(f"Data dir: {settings.data_dir}")
    
    # ---- asyncio, background thread ----
    loop = asyncio.new_event_loop()
    def start_async_loop(loop):
        # start asyncio loop
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    # start asyncio loop in background on new thread
    threading.Thread(target=start_async_loop, args=(loop,), daemon=True).start()
    
    # ---- tkinter ----
    root = tk.Tk()
    root.title(f"{settings.app_name} v{settings.version}")
    app = GUIApp(root, loop)

    try:
        # Start Tkinter's blocking event loop (must run on main thread)
        root.mainloop()
        
    finally:
        logger.info("GUI closed")

    return 0
