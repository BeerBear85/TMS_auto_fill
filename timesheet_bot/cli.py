"""
Command-line interface for the timesheet automation tool.

This module provides the CLI using argparse and orchestrates
the complete fill operation.
"""

import argparse
import sys
from pathlib import Path

from .config import Config
from .csv_loader import load_csv, CSVLoadError
from .playwright_client import run_fill_operation
from .logging_utils import setup_logging, get_logger, log_section, log_error


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='timesheet_bot',
        description='Automated timesheet filling for TMS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - validate CSV without opening browser
  python -m timesheet_bot fill --csv data/week48.csv --dry-run

  # Fill timesheet in headful mode (see browser)
  python -m timesheet_bot fill --csv data/week48.csv

  # Fill timesheet in headless mode
  python -m timesheet_bot fill --csv data/week48.csv --headless

  # Fill with auto-submit (click Promark automatically)
  python -m timesheet_bot fill --csv data/week48.csv --auto-submit

  # Fill without overwriting existing values
  python -m timesheet_bot fill --csv data/week48.csv --no-overwrite

  # Verbose output for debugging
  python -m timesheet_bot fill --csv data/week48.csv --verbose
        """
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Fill command
    fill_parser = subparsers.add_parser(
        'fill',
        help='Fill timesheet from CSV data'
    )

    # Required arguments
    fill_parser.add_argument(
        '--csv',
        type=str,
        required=True,
        metavar='PATH',
        help='Path to CSV file with timesheet data'
    )

    # Optional arguments
    fill_parser.add_argument(
        '--week',
        type=int,
        metavar='NUM',
        help='Week number (1-53)'
    )

    fill_parser.add_argument(
        '--year',
        type=int,
        metavar='YEAR',
        help='Year (e.g., 2025)'
    )

    fill_parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no GUI)'
    )

    fill_parser.add_argument(
        '--auto-submit',
        action='store_true',
        help='Automatically click Promark button after filling'
    )

    fill_parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='Skip fields that already have values'
    )

    fill_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse CSV and show plan without opening browser'
    )

    fill_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging (debug level)'
    )

    return parser


def validate_args(args: argparse.Namespace) -> bool:
    """
    Validate command-line arguments.

    Args:
        args: Parsed arguments

    Returns:
        True if valid, False otherwise
    """
    logger = get_logger()

    # Check for conflicting options
    if args.dry_run and args.auto_submit:
        log_error("Cannot use --auto-submit with --dry-run", logger)
        return False

    # Check CSV file exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        log_error(f"CSV file not found: {args.csv}", logger)
        return False

    return True


def cmd_fill(args: argparse.Namespace) -> int:
    """
    Execute the fill command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger = get_logger()

    # Create configuration from arguments
    config = Config(
        csv_path=args.csv,
        week=args.week,
        year=args.year,
        headless=args.headless,
        auto_submit=args.auto_submit,
        no_overwrite=args.no_overwrite,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    try:
        # Validate configuration
        config.validate()
    except ValueError as e:
        log_error(f"Configuration error: {e}", logger)
        return 1

    # Load CSV data
    log_section("Loading CSV Data", logger)

    try:
        rows = load_csv(config.csv_path)
        logger.info(f"Loaded {len(rows)} row(s) from {config.csv_path}")

        # Display the rows
        logger.info("")
        logger.info("Projects to fill:")
        for i, row in enumerate(rows, 1):
            weekdays_with_values = [
                day for day in ['monday', 'tuesday', 'wednesday', 'thursday',
                               'friday', 'saturday', 'sunday']
                if row.get_weekday_value(day) is not None
            ]
            logger.info(
                f"  {i}. {row.project_number} "
                f"({len(weekdays_with_values)} day(s), "
                f"{row.total_hours():.2f} hours total)"
            )

    except CSVLoadError as e:
        log_error(f"CSV loading failed: {e}", logger)
        return 1

    # Dry run mode - stop here
    if config.dry_run:
        logger.info("")
        log_section("Dry Run Complete", logger)
        logger.info("No browser operations performed.")
        logger.info("Run without --dry-run to execute the fill operation.")
        return 0

    # Execute fill operation
    log_section("Starting Fill Operation", logger)

    try:
        summary = run_fill_operation(config, rows)

        # Display summary
        logger.info(summary.format_summary())

        # Return exit code based on results
        if summary.total_cells_failed > 0 or summary.projects_not_found > 0:
            logger.warning("Operation completed with errors")
            return 1
        else:
            logger.info("Operation completed successfully")
            return 0

    except KeyboardInterrupt:
        logger.info("")
        logger.warning("Operation cancelled by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.info("")
        log_error(f"Operation failed: {e}", logger)
        if config.verbose:
            import traceback
            logger.debug(traceback.format_exc())
        return 1


def main(argv=None):
    """
    Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Set up logging
    setup_logging(verbose=args.verbose if hasattr(args, 'verbose') else False)

    logger = get_logger()

    # Show header
    logger.info("")
    logger.info("=" * 70)
    logger.info("  TMS Timesheet Automation Bot")
    logger.info("=" * 70)

    # Check if command was specified
    if not args.command:
        parser.print_help()
        return 1

    # Validate arguments
    if not validate_args(args):
        return 1

    # Execute command
    if args.command == 'fill':
        return cmd_fill(args)
    else:
        log_error(f"Unknown command: {args.command}", logger)
        return 1


if __name__ == '__main__':
    sys.exit(main())
