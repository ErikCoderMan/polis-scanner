from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.runtime import RuntimeContext

from collections import defaultdict

from src.core.logger import get_logger
from src.core.registry import command, get_commands
from src.ui.log_buffer import log_buffer

logger = get_logger(__name__)

@command(
    name="help",
    usage="help [prefix1 prefix2 prefix3 ...]",
    description=(
        "Display help for all commands or a filtered subset.\n\n"
        "If one or more command prefixes are provided, only commands\n"
        "starting with those prefixes are shown.\n"
        "If no arguments are given, all commands are listed.\n\n"
        "Examples:\n"
        "    help po tas find    → shows: poll, tasks, find\n"
        "    help refresh        → shows: refresh\n"
        "    help                → shows all commands"
    ),
    category="other"
)
async def cmd_help(args=None, ctx=None):
    commands = get_commands()
    grouped = defaultdict(list)
    
    for cmd, meta in commands.items():
        if args:
            if any(cmd.startswith(arg) for arg in args):
                grouped[meta.category].append(meta)
        
        else:
            grouped[meta.category].append(meta)
            
    if not grouped:
        logger.warning("No results for arguments")
        return

    logger.info("Showing help...\n")
    
    showed = 0
    for category in sorted(grouped.keys()):
        log_buffer.write(f"Category {category.capitalize()}:\n")
        
        for meta in sorted(grouped[category], key=lambda m: m.name):
            showed += 1
            space = " " * 4
            log_buffer.write(f"{space}{meta.usage}")
            desc_lines = meta.description.splitlines()
            
            for line in desc_lines:
                space = " " * 8
                log_buffer.write(f"{space}{line}\n")
            
            log_buffer.newline()
            
    logger.info(f"Returned {showed} commands with help")
