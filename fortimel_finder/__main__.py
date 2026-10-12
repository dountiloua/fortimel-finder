import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
