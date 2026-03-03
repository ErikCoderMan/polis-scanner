from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

import asyncio

from src.utils.query import parse_command
from src.core.logger import get_logger
from src.core.scheduler import WorkerAlreadyRunningError
from src.core.lifecycle import graceful_shutdown
from src.api.polis import PolisAPIError

from src.commands.refresh import cmd_refresh
from src.commands.load import cmd_load
from src.commands.more import cmd_more
from src.commands.help import cmd_help
from src.commands.find import cmd_find
from src.commands.search import cmd_search
from src.commands.rank import cmd_rank
from src.commands.clear import cmd_clear
from src.commands.poll import cmd_poll
from src.commands.kill import cmd_kill
from src.commands.tasks import cmd_tasks
from src.commands.exit import cmd_exit

from src.core.registry import get_commands

logger = get_logger(__name__)

# --------------------
# command handler
# --------------------

async def handle_command(text, ctx: RuntimeContext=None):
    cmd, args = parse_command(text)
    
    if not cmd:
        return

    command_map = {
        "refresh": cmd_refresh,
        "load": cmd_load,
        "more": cmd_more,
        "help": cmd_help,
        "find": cmd_find,
        "search": cmd_search,
        "rank": cmd_rank,
        "clear": cmd_clear,
        "poll": cmd_poll,
        "kill": cmd_kill,
        "tasks": cmd_tasks,
        "exit": cmd_exit,
        "quit": cmd_exit
    }
    
    try:
        handler = command_map.get(cmd)

        if not handler:
            logger.warning("Unknown command")
            ctx.state["force_scroll"] = True
            return

        logger.info(f"cmd='{cmd}', args='{' '.join(args)}'")

        try:
            if cmd in ("exit", "quit"):
                # Special case for shutdown to evade recursion loop error
                await handler(args=args, ctx=ctx)
            
            ctx.scheduler.spawn(
                cmd,
                lambda: handler(args=args, ctx=ctx)
            )

        except WorkerAlreadyRunningError:
            logger.warning(f"Command '{cmd}' is already running")
        
        except PolisAPIError:
            logger.error("Polis API error while fetching")
            
    finally:
        ctx.state["force_scroll"] = True
