import sys
import argparse
import asyncio


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("command", nargs="*")
    return parser.parse_args()


async def main_async(args):
    # ---- Direct command mode ----
    if args.command:
        from src.commands.commands import handle_command
        from src.ui.log_buffer import log_buffer

        log_buffer.interactive_mode = False

        class SimpleApp:
            def exit(self, result=0):
                pass

        app = SimpleApp()

        await handle_command(" ".join(args.command), app, interactive=False)

        if log_buffer and len(log_buffer) > 0:
            print("\n".join(str(x) for x in log_buffer))

        return 0

    # ---- Interactive CLI mode ----
    from src.cli.main import run_cli
    return await run_cli()


def main():
    args = parse_args()

    # ---- GUI mode (sync, owns main thread) ----
    if args.gui:
        from src.gui.main import run_gui
        return run_gui()

    # ---- CLI mode (asyncio owns main thread) ----
    return asyncio.run(main_async(args))


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
