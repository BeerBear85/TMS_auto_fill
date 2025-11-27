"""
CSV loader for timesheet data.

This module handles loading and parsing CSV files containing timesheet data.
It validates the format and converts values to the appropriate types.
"""

import csv
from pathlib import Path
from typing import List, Optional

from .models import TimesheetRow


class CSVLoadError(Exception):
    """Raised when CSV loading fails."""
    pass


class CSVLoader:
    """
    Loads timesheet data from CSV files.

    Expected CSV format:
        project_number,project_name,project_task,monday,tuesday,wednesday,thursday,friday,saturday,sunday
        8-26214-10-42,TD_Academy_Simulator,01 - Unspecified,7.40,7.40,7.40,7.40,7.40,,
        8-26214-30-01,PR_Engine,01 - Unspecified,,,,,1.0,,
    """

    REQUIRED_HEADERS = [
        'project_number',
        'project_name',
        'project_task',
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday'
    ]

    def __init__(self, file_path: str):
        """
        Initialize the CSV loader.

        Args:
            file_path: Path to the CSV file

        Raises:
            CSVLoadError: If file doesn't exist
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise CSVLoadError(f"CSV file not found: {file_path}")

    def load(self) -> List[TimesheetRow]:
        """
        Load timesheet rows from the CSV file.

        Returns:
            List of TimesheetRow objects

        Raises:
            CSVLoadError: If CSV format is invalid or data is malformed
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self._validate_headers(reader.fieldnames)
                return self._parse_rows(reader)
        except CSVLoadError:
            raise
        except Exception as e:
            raise CSVLoadError(f"Failed to load CSV: {e}")

    def _validate_headers(self, headers: Optional[List[str]]):
        """
        Validate that CSV has all required headers.

        Args:
            headers: List of header names from CSV

        Raises:
            CSVLoadError: If headers are missing or incorrect
        """
        if not headers:
            raise CSVLoadError("CSV file is empty or has no headers")

        # Normalize headers (strip whitespace, lowercase)
        normalized = [h.strip().lower() for h in headers]

        missing = [h for h in self.REQUIRED_HEADERS if h not in normalized]
        if missing:
            raise CSVLoadError(
                f"CSV missing required headers: {', '.join(missing)}"
            )

    def _parse_rows(self, reader: csv.DictReader) -> List[TimesheetRow]:
        """
        Parse CSV rows into TimesheetRow objects.

        Args:
            reader: CSV DictReader

        Returns:
            List of TimesheetRow objects

        Raises:
            CSVLoadError: If row data is invalid
        """
        rows = []
        for line_num, row_dict in enumerate(reader, start=2):  # Start at 2 (header is line 1)
            try:
                row = self._parse_row(row_dict, line_num)
                if row:  # Skip rows with empty project numbers
                    rows.append(row)
            except ValueError as e:
                raise CSVLoadError(f"Error on line {line_num}: {e}")

        if not rows:
            raise CSVLoadError("CSV file contains no valid data rows")

        return rows

    def _parse_row(self, row_dict: dict, line_num: int) -> Optional[TimesheetRow]:
        """
        Parse a single CSV row into a TimesheetRow object.

        Args:
            row_dict: Dictionary of row data from CSV
            line_num: Line number for error reporting

        Returns:
            TimesheetRow object or None if project number is empty

        Raises:
            ValueError: If data is invalid
        """
        # Normalize keys (strip whitespace, lowercase)
        normalized_dict = {k.strip().lower(): v for k, v in row_dict.items()}

        # Get project number
        project_number = normalized_dict.get('project_number', '')
        project_number = project_number.strip() if project_number else ''
        if not project_number:
            # Skip rows with empty project numbers (allows for blank lines)
            return None

        # Get project name and task (optional fields)
        project_name = normalized_dict.get('project_name', '')
        project_name = project_name.strip() if project_name else ''

        project_task = normalized_dict.get('project_task', '')
        project_task = project_task.strip() if project_task else ''

        # Parse weekday values
        weekdays = {}
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            value = normalized_dict.get(day, '')
            value_str = value.strip() if value is not None else ''
            weekdays[day] = self._parse_hours_value(value_str, day, line_num)

        return TimesheetRow(
            project_number=project_number,
            project_name=project_name,
            project_task=project_task,
            **weekdays
        )

    def _parse_hours_value(self, value: str, field_name: str, line_num: int) -> Optional[float]:
        """
        Parse a hours value from CSV.

        Args:
            value: String value from CSV
            field_name: Name of the field (for error messages)
            line_num: Line number (for error messages)

        Returns:
            Float value or None if empty

        Raises:
            ValueError: If value is not a valid number
        """
        if not value:
            return None

        try:
            hours = float(value)
            if hours < 0:
                raise ValueError(f"Hours value cannot be negative: {value}")
            return hours
        except ValueError as e:
            if "could not convert" in str(e).lower():
                raise ValueError(
                    f"Invalid hours value for {field_name}: '{value}' "
                    f"(must be a number or empty)"
                )
            raise


def load_csv(file_path: str) -> List[TimesheetRow]:
    """
    Convenience function to load a CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        List of TimesheetRow objects

    Raises:
        CSVLoadError: If loading fails
    """
    loader = CSVLoader(file_path)
    return loader.load()
