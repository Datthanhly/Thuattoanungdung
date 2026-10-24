import sys
from a4_evac.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["compare", *sys.argv[1:]]))
