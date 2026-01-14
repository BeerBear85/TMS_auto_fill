"""
Tests for CSV generator module.
"""

import pytest
import csv
from pathlib import Path
import tempfile
import os

from timesheet_bot.csv_generator import (
    ProjectData,
    CSVGenerator,
    CSVGeneratorError,
    generate_csv_template,
    validate_project_data
)


class TestProjectData:
    """Tests for ProjectData dataclass."""

    def test_to_csv_row(self):
        """Test converting ProjectData to CSV row."""
        project = ProjectData(
            project_number="8-26214-10-42",
            project_name="TD_Academy_Simulator_Transition",
            project_task="01 - Unspecified"
        )

        row = project.to_csv_row()

        assert row['project_number'] == "8-26214-10-42"
        assert row['project_name'] == "TD_Academy_Simulator_Transition"
        assert row['project_task'] == "01 - Unspecified"
        assert row['monday'] == '0'
        assert row['tuesday'] == '0'
        assert row['wednesday'] == '0'
        assert row['thursday'] == '0'
        assert row['friday'] == '0'
        assert row['saturday'] == '0'
        assert row['sunday'] == '0'


class TestCSVGenerator:
    """Tests for CSVGenerator class."""

    def test_init_with_new_file(self, tmp_path):
        """Test initialization with a new file."""
        output_file = tmp_path / "test_output.csv"
        generator = CSVGenerator(str(output_file), force=False)
        assert generator.output_path == output_file

    def test_init_with_existing_file_no_force(self, tmp_path):
        """Test initialization fails with existing file when force=False."""
        output_file = tmp_path / "test_output.csv"
        output_file.touch()  # Create the file

        with pytest.raises(CSVGeneratorError, match="already exists"):
            CSVGenerator(str(output_file), force=False)

    def test_init_with_existing_file_with_force(self, tmp_path):
        """Test initialization succeeds with existing file when force=True."""
        output_file = tmp_path / "test_output.csv"
        output_file.touch()  # Create the file

        generator = CSVGenerator(str(output_file), force=True)
        assert generator.output_path == output_file

    def test_generate_success(self, tmp_path):
        """Test successful CSV generation."""
        output_file = tmp_path / "test_output.csv"
        generator = CSVGenerator(str(output_file))

        projects = [
            ProjectData(
                project_number="8-26214-10-42",
                project_name="TD_Academy_Simulator_Transition",
                project_task="01 - Unspecified"
            ),
            ProjectData(
                project_number="8-26214-30-01",
                project_name="PR_Engine Commissioning",
                project_task="01 - Unspecified"
            )
        ]

        result_path = generator.generate(projects)

        # Verify file was created
        assert result_path.exists()

        # Verify CSV contents
        with open(result_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 2

            # Check first row
            assert rows[0]['project_number'] == "8-26214-10-42"
            assert rows[0]['project_name'] == "TD_Academy_Simulator_Transition"
            assert rows[0]['project_task'] == "01 - Unspecified"
            assert rows[0]['monday'] == '0'
            assert rows[0]['sunday'] == '0'

            # Check second row
            assert rows[1]['project_number'] == "8-26214-30-01"
            assert rows[1]['project_name'] == "PR_Engine Commissioning"

    def test_generate_empty_list(self, tmp_path):
        """Test generation fails with empty project list."""
        output_file = tmp_path / "test_output.csv"
        generator = CSVGenerator(str(output_file))

        with pytest.raises(CSVGeneratorError, match="No project data"):
            generator.generate([])

    def test_generate_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if needed."""
        output_file = tmp_path / "subdir" / "test_output.csv"
        generator = CSVGenerator(str(output_file))

        projects = [
            ProjectData(
                project_number="8-26214-10-42",
                project_name="Test Project",
                project_task="01 - Unspecified"
            )
        ]

        result_path = generator.generate(projects)

        assert result_path.exists()
        assert result_path.parent.exists()


class TestValidateProjectData:
    """Tests for validate_project_data function."""

    def test_validate_valid_data(self):
        """Test validation with valid data (canonical field names)."""
        data = {
            'project_number': '8-26214-10-42',
            'project_name': 'TD_Academy_Simulator_Transition',
            'project_task': '01 - Unspecified'
        }

        project = validate_project_data(data)

        assert project.project_number == '8-26214-10-42'
        assert project.project_name == 'TD_Academy_Simulator_Transition'
        assert project.project_task == '01 - Unspecified'

    def test_validate_strips_whitespace(self):
        """Test that whitespace is stripped from fields."""
        data = {
            'project_number': '  8-26214-10-42  ',
            'project_name': '  TD_Academy  ',
            'project_task': '  01 - Unspecified  '
        }

        project = validate_project_data(data)

        assert project.project_number == '8-26214-10-42'
        assert project.project_name == 'TD_Academy'
        assert project.project_task == '01 - Unspecified'

    def test_validate_missing_project_number(self):
        """Test validation fails with missing project_number."""
        data = {
            'project_name': 'TD_Academy_Simulator_Transition',
            'project_task': '01 - Unspecified'
        }

        with pytest.raises(CSVGeneratorError, match="Missing required fields"):
            validate_project_data(data)

    def test_validate_empty_project_number(self):
        """Test validation fails with empty project_number."""
        data = {
            'project_number': '',
            'project_name': 'TD_Academy_Simulator_Transition',
            'project_task': '01 - Unspecified'
        }

        with pytest.raises(CSVGeneratorError, match="Missing required fields"):
            validate_project_data(data)

    def test_validate_legacy_field_names(self):
        """Test validation accepts legacy field names (project_text, task) for backward compatibility."""
        data = {
            'project_number': '8-26214-10-42',
            'project_text': 'TD_Academy_Simulator_Transition',  # Legacy name
            'task': '01 - Unspecified'  # Legacy name
        }

        project = validate_project_data(data)

        # Should be converted to canonical field names internally
        assert project.project_number == '8-26214-10-42'
        assert project.project_name == 'TD_Academy_Simulator_Transition'
        assert project.project_task == '01 - Unspecified'

    def test_validate_mixed_canonical_and_legacy_names(self):
        """Test validation with mix of canonical and legacy names."""
        data = {
            'project_number': '8-26214-10-42',
            'project_text': 'TD_Academy',  # Legacy
            'project_task': '01 - Unspecified'  # Canonical
        }

        project = validate_project_data(data)

        assert project.project_number == '8-26214-10-42'
        assert project.project_name == 'TD_Academy'
        assert project.project_task == '01 - Unspecified'


class TestGenerateCSVTemplate:
    """Tests for generate_csv_template convenience function."""

    def test_generate_template_success(self, tmp_path):
        """Test successful template generation."""
        output_file = tmp_path / "test_template.csv"

        projects_data = [
            {
                'project_number': '8-26214-10-42',
                'project_name': 'TD_Academy_Simulator_Transition',
                'project_task': '01 - Unspecified'
            },
            {
                'project_number': '8-26214-30-01',
                'project_name': 'PR_Engine Commissioning',
                'project_task': '01 - Unspecified'
            }
        ]

        result_path = generate_csv_template(projects_data, str(output_file))

        assert result_path.exists()

        # Verify CSV contents
        with open(result_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2

    def test_generate_template_with_invalid_data(self, tmp_path):
        """Test template generation fails with invalid data."""
        output_file = tmp_path / "test_template.csv"

        projects_data = [
            {
                'project_number': '8-26214-10-42',
                'project_name': 'TD_Academy',
                'project_task': '01 - Unspecified'
            },
            {
                'project_number': '',  # Invalid - empty
                'project_name': 'PR_Engine',
                'project_task': '01 - Unspecified'
            }
        ]

        with pytest.raises(CSVGeneratorError, match="Error in project 2"):
            generate_csv_template(projects_data, str(output_file))

    def test_generate_template_force_overwrite(self, tmp_path):
        """Test template generation with force overwrite."""
        output_file = tmp_path / "test_template.csv"
        output_file.touch()  # Create existing file

        projects_data = [
            {
                'project_number': '8-26214-10-42',
                'project_name': 'TD_Academy',
                'project_task': '01 - Unspecified'
            }
        ]

        result_path = generate_csv_template(
            projects_data,
            str(output_file),
            force=True
        )

        assert result_path.exists()

    def test_csv_header_order(self, tmp_path):
        """Test that CSV header has correct column order (canonical format)."""
        output_file = tmp_path / "test_template.csv"

        projects_data = [
            {
                'project_number': '8-26214-10-42',
                'project_name': 'TD_Academy',
                'project_task': '01 - Unspecified'
            }
        ]

        result_path = generate_csv_template(projects_data, str(output_file))

        # Read and check header
        with open(result_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)

            # Expected header uses canonical field names
            expected_header = [
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

            assert header == expected_header
