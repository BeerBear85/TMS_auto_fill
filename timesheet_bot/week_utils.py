"""
Week utility functions for parsing and manipulating week ranges.

This module provides functions for parsing week range strings,
calculating week offsets, and handling year boundaries.
"""

from typing import List, Tuple
import re


class WeekRangeParseError(Exception):
    """Exception raised when week range parsing fails."""
    pass


def parse_week_range(week_spec: str) -> List[int]:
    """
    Parse a week range specification into a sorted list of unique week numbers.

    Accepted formats:
    - Single weeks: "48" → [48]
    - Comma-separated: "48,49,50" → [48, 49, 50]
    - Ranges: "48-50" → [48, 49, 50]
    - Combined: "48-50,52" → [48, 49, 50, 52]

    Args:
        week_spec: Week specification string

    Returns:
        Sorted list of unique week numbers (integers 1-53)

    Raises:
        WeekRangeParseError: If the format is invalid or week numbers are out of range

    Examples:
        >>> parse_week_range("48")
        [48]
        >>> parse_week_range("48,49,50")
        [48, 49, 50]
        >>> parse_week_range("48-50")
        [48, 49, 50]
        >>> parse_week_range("48-50,52")
        [48, 49, 50, 52]
    """
    if not week_spec or not week_spec.strip():
        raise WeekRangeParseError("Week specification cannot be empty")

    week_spec = week_spec.strip()
    weeks = set()

    # Split by comma
    parts = week_spec.split(',')

    for part in parts:
        part = part.strip()

        if not part:
            raise WeekRangeParseError(f"Invalid week specification: empty part in '{week_spec}'")

        # Check if it's a range (e.g., "48-50")
        if '-' in part:
            range_match = re.match(r'^(\d+)-(\d+)$', part)
            if not range_match:
                raise WeekRangeParseError(
                    f"Invalid range format: '{part}'. Expected format: 'N-M' where N and M are week numbers"
                )

            start_str, end_str = range_match.groups()
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise WeekRangeParseError(f"Invalid week numbers in range: '{part}'")

            if start > end:
                raise WeekRangeParseError(
                    f"Invalid range '{part}': start week ({start}) is greater than end week ({end})"
                )

            # Validate range
            if not (1 <= start <= 53):
                raise WeekRangeParseError(f"Week number {start} out of range (must be 1-53)")
            if not (1 <= end <= 53):
                raise WeekRangeParseError(f"Week number {end} out of range (must be 1-53)")

            # Add all weeks in range
            weeks.update(range(start, end + 1))

        else:
            # Single week number
            if not re.match(r'^\d+$', part):
                raise WeekRangeParseError(f"Invalid week number: '{part}'")

            try:
                week = int(part)
            except ValueError:
                raise WeekRangeParseError(f"Invalid week number: '{part}'")

            if not (1 <= week <= 53):
                raise WeekRangeParseError(f"Week number {week} out of range (must be 1-53)")

            weeks.add(week)

    if not weeks:
        raise WeekRangeParseError(f"No valid week numbers found in '{week_spec}'")

    return sorted(list(weeks))


def calculate_week_offset(baseline_year: int, baseline_week: int,
                         target_year: int, target_week: int) -> int:
    """
    Calculate the offset between a baseline week and a target week.

    This handles year boundaries by converting weeks to a linear index.

    Args:
        baseline_year: Year of the baseline week (e.g., 2025)
        baseline_week: Week number of the baseline (1-53)
        target_year: Year of the target week
        target_week: Week number of the target (1-53)

    Returns:
        Offset in weeks (positive for forward, negative for backward)

    Examples:
        >>> calculate_week_offset(2025, 48, 2025, 50)
        2
        >>> calculate_week_offset(2025, 48, 2025, 46)
        -2
        >>> calculate_week_offset(2025, 52, 2026, 2)
        2  # Assuming 52 weeks in 2025
    """
    # Convert to linear week index (approximate)
    # This is a simplified calculation that assumes 52 weeks per year
    baseline_index = baseline_year * 52 + baseline_week
    target_index = target_year * 52 + target_week

    return target_index - baseline_index


def validate_week_offset(offset: int, max_forward: int = 10, max_backward: int = 20) -> None:
    """
    Validate that a week offset is within allowed bounds.

    Args:
        offset: Week offset (positive for forward, negative for backward)
        max_forward: Maximum allowed forward offset (default: 10)
        max_backward: Maximum allowed backward offset (default: 20)

    Raises:
        ValueError: If offset exceeds allowed bounds
    """
    if offset > max_forward:
        raise ValueError(
            f"Week offset {offset} exceeds maximum forward navigation limit (+{max_forward} weeks)"
        )

    if offset < -max_backward:
        raise ValueError(
            f"Week offset {offset} exceeds maximum backward navigation limit (-{max_backward} weeks)"
        )


def parse_week_display(week_text: str) -> Tuple[int, int]:
    """
    Parse week display text from TMS UI to extract year and week number.

    Expected formats:
    - "Week 48, 2025"
    - "Week 48 2025"
    - "W48 2025"

    Args:
        week_text: Text displayed in the TMS week selector

    Returns:
        Tuple of (year, week_number)

    Raises:
        ValueError: If the text cannot be parsed
    """
    # Try different patterns
    patterns = [
        r'[Ww]eek\s*(\d+)[,\s]+(\d{4})',  # "Week 48, 2025"
        r'[Ww](\d+)\s+(\d{4})',            # "W48 2025"
        r'(\d+)[,\s]+(\d{4})',             # "48, 2025"
    ]

    for pattern in patterns:
        match = re.search(pattern, week_text)
        if match:
            week_num = int(match.group(1))
            year = int(match.group(2))

            if not (1 <= week_num <= 53):
                raise ValueError(f"Invalid week number {week_num} (must be 1-53)")

            if not (2000 <= year <= 2100):
                raise ValueError(f"Invalid year {year}")

            return (year, week_num)

    raise ValueError(f"Could not parse week display text: '{week_text}'")
