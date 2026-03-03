import sys
import argparse
import asyncio
from src.core.runtime import RuntimeContext

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("command", nargs="*")
    
    args, unknown = parser.parse_known_args()
    args.command.extend(unknown)
    
    return args


async def main_async(args):
    """
    If any arguments have been provided
    then run direct mode (one time command execution), then exit.
    Otherwise if no arguments have been provided,
    then start interactive mode that runs until user enters 'exit/quit'
    """
    ctx = RuntimeContext()
    ctx.mode = "cli"
    
    # -----------------------------
    # Non interactive CLI
    # -----------------------------
    if args.command:
        ctx.interactive = False
        from src.core.dispatcher import handle_command
        from src.ui.log_buffer import log_buffer
        
        log_buffer.interactive_mode = False
        
        await handle_command(text=" ".join(args.command), ctx=ctx)
        
        while ctx.scheduler.running_tasks():
            await asyncio.sleep(0.5)

        return 0
    
    # -----------------------------
    # Interactive CLI
    # -----------------------------
    ctx.interactive = True
    
    from src.cli.main import run_cli
    return await run_cli(ctx)


def main():
    """
    (GUI) version (default) is using tkinter.
    (CLI) version (--cli) is using prompt_toolkit.
    """
    
    args = parse_args()
    
    # ---- CLI ----
    if args.cli or args.command:
        return asyncio.run(main_async(args))
    
    # -----------------------------
    # Interactive GUI
    # -----------------------------
    from src.gui.main import run_gui
    
    ctx = RuntimeContext()
    ctx.mode = "gui"
    ctx.interactive = True
        
    return run_gui(ctx)


if __name__ == "__main__":
    try:
        sys.exit(main())

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)

    except Exception:
        import logging
        logging.exception("Fatal unhandled error")
        sys.exit(2)
