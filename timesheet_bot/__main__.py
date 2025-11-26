"""
Main entry point for running the package as a module.

Usage:
    python -m timesheet_bot fill --csv data/week48.csv
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())
