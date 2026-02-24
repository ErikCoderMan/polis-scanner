import sys
import argparse
import asyncio

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("command", nargs="*")
    args = parser.parse_args()

    # ---- GUI mode ----
    if args.gui:
        from src.gui.main import run_gui
        return run_gui()

    # ---- Direct command mode ----
    if args.command:
        from src.cli.commands import handle_command
        from src.ui.log_buffer import log_buffer
        
        log_buffer.interactive_mode = False
        
        class SimpleApp:
            def exit(self, result=0):
                pass

        app = SimpleApp()

        await handle_command(" ".join(args.command), app, interactive=False)
        if log_buffer is not None and len(log_buffer) > 0:
            print("\n".join(str(x) for x in log_buffer))
            
        return 0

    # ---- Interactive CLI mode ----
    from src.cli.main import run_cli
    return await run_cli()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)

    except Exception:
        import logging
        logging.exception("Fatal unhandled error")
        sys.exit(2)
