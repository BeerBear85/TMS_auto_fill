"""
Configuration for the timesheet automation tool.

This module centralizes configuration values including URLs,
timeouts, and default settings.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Config:
    """
    Application configuration.

    Attributes:
        tms_url: URL of the Timesheet Management System
        page_load_timeout: Timeout for page loads (milliseconds)
        element_timeout: Timeout for element operations (milliseconds)
        navigation_timeout: Timeout for navigation (milliseconds)
        headless: Whether to run browser in headless mode
        auto_submit: Whether to auto-submit after filling
        no_overwrite: Whether to skip non-empty fields
        dry_run: Whether to run in dry-run mode (no browser)
        verbose: Whether to enable verbose logging
        csv_path: Path to the CSV file
        week: Week number (optional)
        year: Year (optional)
    """
    tms_url: str = "https://tms.md-man.biz/home"
    page_load_timeout: int = 30000  # 30 seconds
    element_timeout: int = 10000    # 10 seconds
    navigation_timeout: int = 30000  # 30 seconds

    # CLI options
    headless: bool = False
    auto_submit: bool = False
    no_overwrite: bool = False
    dry_run: bool = False
    verbose: bool = False

    # Data options
    csv_path: Optional[str] = None
    week: Optional[int] = None
    year: Optional[int] = None
    weeks: Optional[List[int]] = None

    def validate(self):
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.dry_run and self.auto_submit:
            raise ValueError("Cannot use --auto-submit with --dry-run")

        if self.csv_path is None:
            raise ValueError("CSV path is required")

        if self.week is not None and not (1 <= self.week <= 53):
            raise ValueError(f"Week must be between 1 and 53, got: {self.week}")

        if self.year is not None and not (2000 <= self.year <= 2100):
            raise ValueError(f"Year must be between 2000 and 2100, got: {self.year}")

        # Validate weeks list if provided
        if self.weeks is not None:
            if not isinstance(self.weeks, list):
                raise ValueError("weeks must be a list")
            if len(self.weeks) == 0:
                raise ValueError("weeks list cannot be empty")
            for w in self.weeks:
                if not (1 <= w <= 53):
                    raise ValueError(f"Week number {w} out of range (must be 1-53)")


# Default configuration instance
DEFAULT_CONFIG = Config()
