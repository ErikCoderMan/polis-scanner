import sys
import argparse
import asyncio

from src.cli import run_cli
from src.gui import run_gui


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if args.gui:
        # GUI not async for now
        return run_gui()
    else:
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
