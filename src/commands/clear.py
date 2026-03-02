from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer

logger = get_logger(__name__)

async def cmd_clear(args=None, ctx: RuntimeContext=None):
    async def _run():
        logger.info("Clearing screen...") # still being written to file log
        log_buffer.clear()

    await _run()
