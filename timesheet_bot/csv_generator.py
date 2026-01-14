"""
CSV generator for creating timesheet templates from TMS table data.

This module handles extraction of project data from the TMS table
and generation of CSV templates with zero-filled weekday columns.
"""

import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from .csv_schema import CSVSchema


@dataclass
class ProjectData:
    """
    Represents extracted project data from TMS table.

    Attributes:
        project_number: Full project number (e.g., "8-26214-10-42")
        project_name: Project name/description
        project_task: Task description (e.g., "01 – Unspecified")
    """
    project_number: str
    project_name: str
    project_task: str

    def to_csv_row(self) -> Dict[str, str]:
        """
        Convert to CSV row dictionary with zero-filled weekdays.

        Returns:
            Dictionary with all CSV columns using canonical headers
        """
        return {
            CSVSchema.PROJECT_NUMBER: self.project_number,
            CSVSchema.PROJECT_NAME: self.project_name,
            CSVSchema.PROJECT_TASK: self.project_task,
            CSVSchema.MONDAY: '0',
            CSVSchema.TUESDAY: '0',
            CSVSchema.WEDNESDAY: '0',
            CSVSchema.THURSDAY: '0',
            CSVSchema.FRIDAY: '0',
            CSVSchema.SATURDAY: '0',
            CSVSchema.SUNDAY: '0',
        }


class CSVGeneratorError(Exception):
    """Raised when CSV generation fails."""
    pass


class CSVGenerator:
    """
    Generates CSV templates from extracted TMS table data.

    Uses canonical headers from CSVSchema for consistency with CSV loader.
    """

    # CSV header columns in correct order (from central schema)
    CSV_HEADERS = CSVSchema.CANONICAL_HEADERS

    def __init__(self, output_path: str, force: bool = False):
        """
        Initialize the CSV generator.

        Args:
            output_path: Path where CSV will be saved
            force: Whether to overwrite existing file

        Raises:
            CSVGeneratorError: If file exists and force is False
        """
        self.output_path = Path(output_path)
        self.force = force

        # Validate output path
        if self.output_path.exists() and not self.force:
            raise CSVGeneratorError(
                f"Error: Output file already exists. Use --force to overwrite."
            )

    def generate(self, projects: List[ProjectData]) -> Path:
        """
        Generate CSV template from project data.

        Args:
            projects: List of extracted project data

        Returns:
            Path to the generated CSV file

        Raises:
            CSVGeneratorError: If generation fails
        """
        if not projects:
            raise CSVGeneratorError("No project data to generate CSV from")

        try:
            # Ensure parent directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write CSV file using schema encoding standards
            with open(self.output_path, 'w', encoding=CSVSchema.ENCODING, newline=CSVSchema.NEWLINE) as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)

                # Write header
                writer.writeheader()

                # Write each project row
                for project in projects:
                    writer.writerow(project.to_csv_row())

            return self.output_path.absolute()

        except Exception as e:
            raise CSVGeneratorError(f"Failed to write CSV file: {e}")


def validate_project_data(data: Dict[str, str]) -> ProjectData:
    """
    Validate and convert raw project data to ProjectData object.

    Supports both canonical and legacy field names for backward compatibility.

    Args:
        data: Raw dictionary with project information

    Returns:
        Validated ProjectData object

    Raises:
        CSVGeneratorError: If required fields are missing or invalid
    """
    # Normalize keys to handle both canonical and legacy names
    normalized_data = {}
    for key, value in data.items():
        canonical_key = CSVSchema.normalize_header(key)
        normalized_data[canonical_key] = value

    # Check required fields (using canonical names)
    required_fields = [
        CSVSchema.PROJECT_NUMBER,
        CSVSchema.PROJECT_NAME,
        CSVSchema.PROJECT_TASK
    ]
    missing = [f for f in required_fields if f not in normalized_data or not normalized_data[f]]

    if missing:
        raise CSVGeneratorError(
            f"Missing required fields: {', '.join(missing)}"
        )

    # Create and validate ProjectData
    try:
        project = ProjectData(
            project_number=normalized_data[CSVSchema.PROJECT_NUMBER].strip(),
            project_name=normalized_data[CSVSchema.PROJECT_NAME].strip(),
            project_task=normalized_data[CSVSchema.PROJECT_TASK].strip()
        )

        if not project.project_number:
            raise CSVGeneratorError("Project number cannot be empty")

        return project

    except Exception as e:
        raise CSVGeneratorError(f"Invalid project data: {e}")


def generate_csv_template(
    projects_data: List[Dict[str, str]],
    output_path: str,
    force: bool = False
) -> Path:
    """
    Convenience function to generate CSV template from raw project data.

    Args:
        projects_data: List of raw project dictionaries
        output_path: Path where CSV will be saved
        force: Whether to overwrite existing file

    Returns:
        Path to the generated CSV file

    Raises:
        CSVGeneratorError: If generation fails
    """
    # Validate and convert all project data
    validated_projects = []
    for i, data in enumerate(projects_data, 1):
        try:
            project = validate_project_data(data)
            validated_projects.append(project)
        except CSVGeneratorError as e:
            raise CSVGeneratorError(f"Error in project {i}: {e}")

    # Generate CSV
    generator = CSVGenerator(output_path, force=force)
    return generator.generate(validated_projects)
