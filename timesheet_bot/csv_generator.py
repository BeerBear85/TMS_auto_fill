"""
CSV generator for creating timesheet templates from TMS table data.

This module handles extraction of project data from the TMS table
and generation of CSV templates with zero-filled weekday columns.
"""

import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ProjectData:
    """
    Represents extracted project data from TMS table.

    Attributes:
        project_number: Full project number (e.g., "8-26214-10-42")
        project_text: Project name/description
        task: Task description (e.g., "01 – Unspecified")
    """
    project_number: str
    project_text: str
    task: str

    def to_csv_row(self) -> Dict[str, str]:
        """
        Convert to CSV row dictionary with zero-filled weekdays.

        Returns:
            Dictionary with all CSV columns
        """
        return {
            'project_number': self.project_number,
            'project_text': self.project_text,
            'task': self.task,
            'monday': '0',
            'tuesday': '0',
            'wednesday': '0',
            'thursday': '0',
            'friday': '0',
            'saturday': '0',
            'sunday': '0',
        }


class CSVGeneratorError(Exception):
    """Raised when CSV generation fails."""
    pass


class CSVGenerator:
    """
    Generates CSV templates from extracted TMS table data.
    """

    # CSV header columns in correct order
    CSV_HEADERS = [
        'project_number',
        'project_text',
        'task',
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday'
    ]

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

            # Write CSV file
            with open(self.output_path, 'w', encoding='utf-8', newline='') as f:
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

    Args:
        data: Raw dictionary with project information

    Returns:
        Validated ProjectData object

    Raises:
        CSVGeneratorError: If required fields are missing or invalid
    """
    # Check required fields
    required_fields = ['project_number', 'project_text', 'task']
    missing = [f for f in required_fields if f not in data or not data[f]]

    if missing:
        raise CSVGeneratorError(
            f"Missing required fields: {', '.join(missing)}"
        )

    # Create and validate ProjectData
    try:
        project = ProjectData(
            project_number=data['project_number'].strip(),
            project_text=data['project_text'].strip(),
            task=data['task'].strip()
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
