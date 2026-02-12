import sys
from src.cli import run_cli
from src.gui import run_gui
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if args.gui:
        return run_gui()
    else:
        return run_cli()


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
