from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.core.registry import command

logger = get_logger(__name__)

@command(
    name="clear",
    usage="clear",
    description="Clear the output screen.",
    category="other"
)
async def cmd_clear(args=None, ctx: RuntimeContext=None):
    logger.info("Clearing screen...") # still being written to file log
    log_buffer.clear()
    
