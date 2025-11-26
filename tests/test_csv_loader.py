"""
Tests for CSV loader functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from timesheet_bot.csv_loader import CSVLoader, CSVLoadError, load_csv
from timesheet_bot.models import TimesheetRow


class TestCSVLoader:
    """Tests for the CSVLoader class."""

    def test_load_valid_csv(self, tmp_path):
        """Test loading a valid CSV file."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,7.40,7.40,7.40,7.40,7.40,,
8-26214-30-01,,,,,1.0,,
8-26245-04-01,2.5,2.5,2.5,2.5,2.5,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))
        rows = loader.load()

        assert len(rows) == 3
        assert rows[0].project_number == "8-26214-10-42"
        assert rows[0].monday == 7.40
        assert rows[0].saturday is None
        assert rows[1].project_number == "8-26214-30-01"
        assert rows[1].friday == 1.0
        assert rows[1].monday is None

    def test_load_csv_with_empty_rows(self, tmp_path):
        """Test that empty rows are skipped."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,7.40,,,,,
,1.0,2.0,3.0,4.0,5.0,,
8-26245-04-01,2.5,,,,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))
        rows = loader.load()

        # Should skip the row with empty project number
        assert len(rows) == 2
        assert rows[0].project_number == "8-26214-10-42"
        assert rows[1].project_number == "8-26245-04-01"

    def test_invalid_hours_value(self, tmp_path):
        """Test that invalid hours values raise an error."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,invalid,7.40,7.40,7.40,7.40,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))

        with pytest.raises(CSVLoadError) as exc_info:
            loader.load()

        assert "Invalid hours value" in str(exc_info.value)
        assert "line 2" in str(exc_info.value)

    def test_negative_hours_value(self, tmp_path):
        """Test that negative hours values raise an error."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,-5.0,7.40,7.40,7.40,7.40,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))

        with pytest.raises(CSVLoadError) as exc_info:
            loader.load()

        assert "cannot be negative" in str(exc_info.value)

    def test_missing_headers(self, tmp_path):
        """Test that missing headers raise an error."""
        csv_content = """project_number,monday,tuesday
8-26214-10-42,7.40,7.40"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))

        with pytest.raises(CSVLoadError) as exc_info:
            loader.load()

        assert "missing required headers" in str(exc_info.value).lower()

    def test_file_not_found(self):
        """Test that non-existent file raises an error."""
        with pytest.raises(CSVLoadError) as exc_info:
            CSVLoader("/nonexistent/file.csv")

        assert "not found" in str(exc_info.value)

    def test_empty_csv(self, tmp_path):
        """Test that empty CSV raises an error."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))

        with pytest.raises(CSVLoadError) as exc_info:
            loader.load()

        assert "no valid data rows" in str(exc_info.value).lower()

    def test_decimal_values(self, tmp_path):
        """Test that decimal values are parsed correctly."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,7.5,8.25,6.75,7,7.40,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))
        rows = loader.load()

        assert rows[0].monday == 7.5
        assert rows[0].tuesday == 8.25
        assert rows[0].wednesday == 6.75
        assert rows[0].thursday == 7.0

    def test_convenience_function(self, tmp_path):
        """Test the load_csv convenience function."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,7.40,7.40,7.40,7.40,7.40,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        rows = load_csv(str(csv_file))

        assert len(rows) == 1
        assert rows[0].project_number == "8-26214-10-42"

    def test_whitespace_handling(self, tmp_path):
        """Test that whitespace in values is handled correctly."""
        csv_content = """project_number,monday,tuesday,wednesday,thursday,friday,saturday,sunday
  8-26214-10-42  , 7.40 ,  ,7.40,7.40,7.40,,"""

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader(str(csv_file))
        rows = loader.load()

        assert rows[0].project_number == "8-26214-10-42"
        assert rows[0].monday == 7.40
        assert rows[0].tuesday is None  # Empty after stripping


class TestTimesheetRow:
    """Tests for the TimesheetRow model."""

    def test_total_hours(self):
        """Test total hours calculation."""
        row = TimesheetRow(
            project_number="8-26214-10-42",
            monday=7.40,
            tuesday=7.40,
            wednesday=7.40,
            thursday=7.40,
            friday=7.40
        )

        assert row.total_hours() == 37.0

    def test_get_weekday_value(self):
        """Test getting individual weekday values."""
        row = TimesheetRow(
            project_number="8-26214-10-42",
            monday=7.40,
            friday=5.0
        )

        assert row.get_weekday_value('monday') == 7.40
        assert row.get_weekday_value('tuesday') is None
        assert row.get_weekday_value('friday') == 5.0

    def test_get_all_weekdays(self):
        """Test getting all weekday values."""
        row = TimesheetRow(
            project_number="8-26214-10-42",
            monday=7.40,
            friday=5.0
        )

        weekdays = row.get_all_weekdays()

        assert weekdays['monday'] == 7.40
        assert weekdays['tuesday'] is None
        assert weekdays['friday'] == 5.0
        assert len(weekdays) == 7

    def test_empty_project_number(self):
        """Test that empty project number raises an error."""
        with pytest.raises(ValueError) as exc_info:
            TimesheetRow(project_number="")

        assert "cannot be empty" in str(exc_info.value)
