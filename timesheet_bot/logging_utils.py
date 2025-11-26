"""
Logging utilities for the timesheet automation tool.

This module sets up structured logging with appropriate levels and formats.
"""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels for terminal output.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format log record with colors."""
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )

        # Format the message
        formatted = super().format(record)

        # Reset levelname to avoid side effects
        record.levelname = levelname

        return formatted


def setup_logging(verbose: bool = False, use_colors: bool = True) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        verbose: If True, set level to DEBUG; otherwise INFO
        use_colors: If True, use colored output for terminal

    Returns:
        Configured logger instance
    """
    # Get logger
    logger = logging.getLogger('timesheet_bot')

    # Set level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    if use_colors and sys.stdout.isatty():
        # Use colored formatter for terminal
        formatter = ColoredFormatter(
            fmt='%(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Use plain formatter for redirected output
        formatter = logging.Formatter(
            fmt='%(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger() -> logging.Logger:
    """
    Get the application logger.

    Returns:
        Logger instance
    """
    return logging.getLogger('timesheet_bot')


class LogContext:
    """
    Context manager for temporary log level changes.

    Example:
        >>> logger = get_logger()
        >>> with LogContext(logging.DEBUG):
        ...     logger.debug("This will be shown")
    """

    def __init__(self, level: int):
        """
        Initialize context.

        Args:
            level: Logging level to set temporarily
        """
        self.level = level
        self.original_level: Optional[int] = None
        self.logger = get_logger()

    def __enter__(self):
        """Enter context - save current level and set new one."""
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original level."""
        if self.original_level is not None:
            self.logger.setLevel(self.original_level)


def log_section(title: str, logger: Optional[logging.Logger] = None):
    """
    Log a section header for better readability.

    Args:
        title: Section title
        logger: Logger instance (uses default if None)
    """
    if logger is None:
        logger = get_logger()

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)


def log_step(step: str, logger: Optional[logging.Logger] = None):
    """
    Log a processing step.

    Args:
        step: Step description
        logger: Logger instance (uses default if None)
    """
    if logger is None:
        logger = get_logger()

    logger.info(f"→ {step}")


def log_error(error: str, logger: Optional[logging.Logger] = None):
    """
    Log an error message with consistent formatting.

    Args:
        error: Error message
        logger: Logger instance (uses default if None)
    """
    if logger is None:
        logger = get_logger()

    logger.error(f"✗ {error}")


def log_success(message: str, logger: Optional[logging.Logger] = None):
    """
    Log a success message.

    Args:
        message: Success message
        logger: Logger instance (uses default if None)
    """
    if logger is None:
        logger = get_logger()

    logger.info(f"✓ {message}")


def log_warning(warning: str, logger: Optional[logging.Logger] = None):
    """
    Log a warning message.

    Args:
        warning: Warning message
        logger: Logger instance (uses default if None)
    """
    if logger is None:
        logger = get_logger()

    logger.warning(f"⚠ {warning}")
