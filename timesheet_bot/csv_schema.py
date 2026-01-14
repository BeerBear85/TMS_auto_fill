"""
Central CSV schema definition for timesheet data.

This module defines the single source of truth for CSV format,
including canonical headers, legacy aliases, and migration handling.
"""

from typing import Dict, List, Optional


class CSVSchema:
    """
    Defines the canonical CSV format for timesheet data.

    This is the single source of truth for CSV headers and format.
    All CSV generation and parsing should use this schema.
    """

    # Canonical column names (standard format)
    PROJECT_NUMBER = 'project_number'
    PROJECT_NAME = 'project_name'
    PROJECT_TASK = 'project_task'
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'

    # Canonical headers in correct order
    CANONICAL_HEADERS: List[str] = [
        PROJECT_NUMBER,
        PROJECT_NAME,
        PROJECT_TASK,
        MONDAY,
        TUESDAY,
        WEDNESDAY,
        THURSDAY,
        FRIDAY,
        SATURDAY,
        SUNDAY,
    ]

    # Legacy header aliases (for backward compatibility)
    # Maps legacy header names to canonical names
    LEGACY_ALIASES: Dict[str, str] = {
        'project_text': PROJECT_NAME,  # Old generator used 'project_text'
        'task': PROJECT_TASK,           # Old generator used 'task'
    }

    # CSV format standards
    ENCODING = 'utf-8'
    DELIMITER = ','
    NEWLINE = ''  # Use '' for universal newline mode in Python's csv module

    @classmethod
    def normalize_header(cls, header: str) -> str:
        """
        Normalize a header name to canonical form.

        Handles:
        - Whitespace stripping
        - Lowercase conversion
        - Legacy alias mapping

        Args:
            header: Raw header name from CSV

        Returns:
            Canonical header name

        Examples:
            >>> CSVSchema.normalize_header('  Project_Name  ')
            'project_name'
            >>> CSVSchema.normalize_header('project_text')
            'project_name'
            >>> CSVSchema.normalize_header('task')
            'project_task'
        """
        normalized = header.strip().lower()
        # Map legacy alias to canonical name
        return cls.LEGACY_ALIASES.get(normalized, normalized)

    @classmethod
    def validate_headers(cls, headers: List[str]) -> tuple[bool, Optional[str]]:
        """
        Validate that all required headers are present.

        Accepts both canonical and legacy header names.

        Args:
            headers: List of header names from CSV

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, error_message) if invalid

        Examples:
            >>> CSVSchema.validate_headers(['project_number', 'project_name', ...])
            (True, None)
            >>> CSVSchema.validate_headers(['project_number', 'project_text', ...])
            (True, None)  # Accepts legacy alias
            >>> CSVSchema.validate_headers(['project_number', 'monday'])
            (False, "CSV missing required headers: project_name, project_task, ...")
        """
        if not headers:
            return False, "CSV file is empty or has no headers"

        # Normalize all headers
        normalized_headers = [cls.normalize_header(h) for h in headers]

        # Check for missing required headers
        missing = [h for h in cls.CANONICAL_HEADERS if h not in normalized_headers]

        if missing:
            return False, f"CSV missing required headers: {', '.join(missing)}"

        return True, None

    @classmethod
    def create_header_mapping(cls, csv_headers: List[str]) -> Dict[str, str]:
        """
        Create a mapping from CSV headers to canonical headers.

        This handles legacy aliases automatically.

        Args:
            csv_headers: Actual headers from the CSV file

        Returns:
            Dictionary mapping CSV header -> canonical header

        Examples:
            >>> CSVSchema.create_header_mapping(['project_text', 'task'])
            {'project_text': 'project_name', 'task': 'project_task'}
        """
        mapping = {}
        for header in csv_headers:
            canonical = cls.normalize_header(header)
            mapping[header.strip().lower()] = canonical
        return mapping

    @classmethod
    def get_weekday_headers(cls) -> List[str]:
        """
        Get list of weekday column names in order.

        Returns:
            List of weekday headers [monday, tuesday, ...]
        """
        return [
            cls.MONDAY,
            cls.TUESDAY,
            cls.WEDNESDAY,
            cls.THURSDAY,
            cls.FRIDAY,
            cls.SATURDAY,
            cls.SUNDAY,
        ]


# Convenience constants for external use
CANONICAL_HEADERS = CSVSchema.CANONICAL_HEADERS
LEGACY_ALIASES = CSVSchema.LEGACY_ALIASES
ENCODING = CSVSchema.ENCODING
DELIMITER = CSVSchema.DELIMITER
