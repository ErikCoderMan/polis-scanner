from src.cli import run_cli
from src.gui import run_gui
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    
    if args.gui:
        run_gui()
        
    else:
        run_cli()

if __name__ == "__main__":
    main()
