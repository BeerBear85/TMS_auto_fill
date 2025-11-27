"""
Data models for timesheet automation.

This module defines the data structures used throughout the application,
including timesheet rows, fill results, and summary statistics.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class TimesheetRow:
    """
    Represents a single row of timesheet data from CSV.

    Attributes:
        project_number: Full project number (e.g., "8-26214-10-42")
        project_name: Project name/description (e.g., "TD_Academy_Simulator_Transition")
        project_task: Task description (e.g., "01 - Unspecified")
        monday: Hours for Monday (None if empty)
        tuesday: Hours for Tuesday (None if empty)
        wednesday: Hours for Wednesday (None if empty)
        thursday: Hours for Thursday (None if empty)
        friday: Hours for Friday (None if empty)
        saturday: Hours for Saturday (None if empty)
        sunday: Hours for Sunday (None if empty)
    """
    project_number: str
    project_name: str = ""
    project_task: str = ""
    monday: Optional[float] = None
    tuesday: Optional[float] = None
    wednesday: Optional[float] = None
    thursday: Optional[float] = None
    friday: Optional[float] = None
    saturday: Optional[float] = None
    sunday: Optional[float] = None

    def __post_init__(self):
        """Validate project number is not empty."""
        if not self.project_number or not self.project_number.strip():
            raise ValueError("Project number cannot be empty")
        self.project_number = self.project_number.strip()
        self.project_name = self.project_name.strip()
        self.project_task = self.project_task.strip()

    def get_weekday_value(self, weekday: str) -> Optional[float]:
        """
        Get the hours value for a specific weekday.

        Args:
            weekday: Name of the weekday (lowercase)

        Returns:
            Hours value or None if not set
        """
        return getattr(self, weekday.lower())

    def get_all_weekdays(self) -> Dict[str, Optional[float]]:
        """
        Get all weekday values as a dictionary.

        Returns:
            Dictionary mapping weekday names to hour values
        """
        return {
            'monday': self.monday,
            'tuesday': self.tuesday,
            'wednesday': self.wednesday,
            'thursday': self.thursday,
            'friday': self.friday,
            'saturday': self.saturday,
            'sunday': self.sunday,
        }

    def total_hours(self) -> float:
        """Calculate total hours across all days."""
        return sum(h for h in self.get_all_weekdays().values() if h is not None)


@dataclass
class CellFillResult:
    """
    Result of filling a single cell.

    Attributes:
        project_number: Project identifier
        weekday: Day of week
        value: Hours value filled
        success: Whether the fill was successful
        skipped: Whether the cell was skipped (e.g., due to no-overwrite)
        error: Error message if unsuccessful
    """
    project_number: str
    weekday: str
    value: Optional[float]
    success: bool
    skipped: bool = False
    error: Optional[str] = None


@dataclass
class ProjectFillResult:
    """
    Result of filling all cells for a single project.

    Attributes:
        project_number: Project identifier
        cells_filled: Number of cells successfully filled
        cells_skipped: Number of cells skipped
        cells_failed: Number of cells that failed
        cell_results: Individual cell fill results
        project_found: Whether the project row was found in the table
        error: Error message if project not found
    """
    project_number: str
    cells_filled: int = 0
    cells_skipped: int = 0
    cells_failed: int = 0
    cell_results: List[CellFillResult] = field(default_factory=list)
    project_found: bool = True
    error: Optional[str] = None


@dataclass
class FillSummary:
    """
    Summary of the entire fill operation.

    Attributes:
        total_projects: Total number of projects processed
        projects_found: Number of projects found in the table
        projects_not_found: Number of projects not found
        total_cells_filled: Total cells successfully filled
        total_cells_skipped: Total cells skipped
        total_cells_failed: Total cells that failed
        project_results: Individual project fill results
        missing_projects: List of project numbers not found
        daily_totals: Total hours per weekday
    """
    total_projects: int = 0
    projects_found: int = 0
    projects_not_found: int = 0
    total_cells_filled: int = 0
    total_cells_skipped: int = 0
    total_cells_failed: int = 0
    project_results: List[ProjectFillResult] = field(default_factory=list)
    missing_projects: List[str] = field(default_factory=list)
    daily_totals: Dict[str, float] = field(default_factory=dict)

    def add_project_result(self, result: ProjectFillResult):
        """Add a project result to the summary."""
        self.project_results.append(result)
        self.total_projects += 1

        if result.project_found:
            self.projects_found += 1
            self.total_cells_filled += result.cells_filled
            self.total_cells_skipped += result.cells_skipped
            self.total_cells_failed += result.cells_failed
        else:
            self.projects_not_found += 1
            self.missing_projects.append(result.project_number)

    def calculate_daily_totals(self, rows: List[TimesheetRow]):
        """Calculate total hours per weekday from the input rows."""
        totals = {
            'monday': 0.0,
            'tuesday': 0.0,
            'wednesday': 0.0,
            'thursday': 0.0,
            'friday': 0.0,
            'saturday': 0.0,
            'sunday': 0.0,
        }

        for row in rows:
            for weekday, value in row.get_all_weekdays().items():
                if value is not None:
                    totals[weekday] += value

        self.daily_totals = totals

    def format_summary(self) -> str:
        """
        Format the summary as a human-readable string.

        Returns:
            Formatted summary text
        """
        lines = [
            "\n" + "="*60,
            "FILL OPERATION SUMMARY",
            "="*60,
            f"\nProjects:",
            f"  Total: {self.total_projects}",
            f"  Found: {self.projects_found}",
            f"  Not Found: {self.projects_not_found}",
            f"\nCells:",
            f"  Filled: {self.total_cells_filled}",
            f"  Skipped: {self.total_cells_skipped}",
            f"  Failed: {self.total_cells_failed}",
        ]

        if self.missing_projects:
            lines.append(f"\nMissing Projects:")
            for proj in self.missing_projects:
                lines.append(f"  - {proj}")

        if self.daily_totals:
            lines.append(f"\nDaily Totals:")
            for day, total in self.daily_totals.items():
                lines.append(f"  {day.capitalize()}: {total:.2f} hours")

        lines.append("="*60 + "\n")
        return "\n".join(lines)
