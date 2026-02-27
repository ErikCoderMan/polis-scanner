import sys
import argparse
import asyncio


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true")
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
    
    # -----------------------------
    # Direct command mode
    # -----------------------------
    if args.command:
        from src.commands.commands import handle_command
        from src.ui.log_buffer import log_buffer

        log_buffer.interactive_mode = False
        
        await handle_command(" ".join(args.command), interactive=False)

        if log_buffer and len(log_buffer) > 0:
            print("\n".join(str(x) for x in log_buffer))

        return 0
    
    # -----------------------------
    # Interactive CLI mode
    # -----------------------------
    from src.cli.main import run_cli
    return await run_cli()


def main():
    """
    (GUI) version (default) is using tkinter.
    (CLI) version (--cli) is using prompt_toolkit.
    """
    
    args = parse_args()
    
    # ---- CLI mode ----
    if args.cli or args.command:
        return asyncio.run(main_async(args))
    
    # ---- GUI mode (default) ----
    from src.gui.main import run_gui
    return run_gui()


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
