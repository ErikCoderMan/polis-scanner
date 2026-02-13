import sys
import argparse
import asyncio


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if args.gui:
        # GUI not async yet, will add soon
        from src.gui.main import run_gui
        return run_gui()
    else:
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
