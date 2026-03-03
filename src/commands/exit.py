from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

from src.core.logger import get_logger
from src.ui.log_buffer import log_buffer
from src.core.lifecycle import graceful_shutdown
from src.core.registry import command

logger = get_logger(__name__)

@command(
    name="exit",
    usage="exit / quit [now]",
    description=(
        "Quit the program.\n\n"
        "Options:\n"
        "    now            → Do not wait for background tasks, quit immediately\n"
        "    (no arguments) → Program will make a clean exit and properly close tasks"
    ),
    category="other"
)
async def cmd_exit(args, ctx: RunetimeContext):
    logger.info("Initiating shutdown")
    
    if "now" in args:
        logger.warning("Forcing shutdown with 'now' argument")
        await graceful_shutdown(ctx=ctx, force=True)
    
    else:
        logger.info("Performing graceful shutdown")
        await graceful_shutdown(ctx=ctx, force=False)
