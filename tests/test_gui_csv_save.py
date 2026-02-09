"""
Integration tests for GUI CSV save functionality.

Tests the complete workflow of loading, editing, and saving CSV files
through the GUI.
"""

import pytest
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from timesheet_bot.gui import TimesheetGUI
from timesheet_bot.csv_loader import load_csv
from timesheet_bot.csv_schema import CSVSchema
from timesheet_bot.models import TimesheetRow


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication instance for GUI tests."""
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit - let pytest handle cleanup


class TestGUICSVSaving:
    """Integration tests for CSV save functionality."""

    def test_write_csv_file_preserves_canonical_headers(self, tmp_path):
        """Test that saved CSV uses canonical headers."""
        # Create test data
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test Project",
                project_task="01 - Unspecified",
                monday=7.40,
                tuesday=7.40
            )
        ]

        # Create GUI instance and save
        gui = TimesheetGUI()
        gui.rows = rows
        gui.csv_path = None

        output_file = tmp_path / "test_output.csv"
        gui._write_csv_file(str(output_file))

        # Load file and verify headers
        import csv
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)

            assert header == CSVSchema.CANONICAL_HEADERS, \
                "Saved CSV should use canonical headers from CSVSchema"

    def test_write_csv_file_preserves_data_integrity(self, tmp_path):
        """Test that saved CSV can be reloaded with same data."""
        # Create test data with various values
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test Project 1",
                project_task="01 - Unspecified",
                monday=7.40,
                tuesday=7.40,
                wednesday=7.40,
                thursday=7.40,
                friday=7.40
            ),
            TimesheetRow(
                project_number="8-26214-30-01",
                project_name="Test Project 2",
                project_task="02 - Development",
                monday=2.5,
                friday=1.5
            ),
            TimesheetRow(
                project_number="8-26245-04-01",
                project_name="Test Project 3",
                project_task="03 - Testing",
                # All days None
            )
        ]

        # Save to file
        gui = TimesheetGUI()
        gui.rows = rows

        output_file = tmp_path / "test_roundtrip.csv"
        gui._write_csv_file(str(output_file))

        # Reload with CSV loader
        reloaded_rows = load_csv(str(output_file))

        # Verify all data matches
        assert len(reloaded_rows) == len(rows)

        for original, reloaded in zip(rows, reloaded_rows):
            assert original.project_number == reloaded.project_number
            assert original.project_name == reloaded.project_name
            assert original.project_task == reloaded.project_task
            assert original.monday == reloaded.monday
            assert original.tuesday == reloaded.tuesday
            assert original.wednesday == reloaded.wednesday
            assert original.thursday == reloaded.thursday
            assert original.friday == reloaded.friday
            assert original.saturday == reloaded.saturday
            assert original.sunday == reloaded.sunday

    def test_write_csv_file_handles_empty_cells(self, tmp_path):
        """Test that None values become empty strings in CSV."""
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task",
                monday=7.40,
                tuesday=None,  # Empty
                wednesday=0.0,  # Zero
                thursday=None   # Empty
            )
        ]

        gui = TimesheetGUI()
        gui.rows = rows

        output_file = tmp_path / "test_empty.csv"
        gui._write_csv_file(str(output_file))

        # Reload and verify
        reloaded = load_csv(str(output_file))
        assert len(reloaded) == 1
        assert reloaded[0].monday == 7.40
        assert reloaded[0].tuesday is None
        assert reloaded[0].wednesday == 0.0
        assert reloaded[0].thursday is None

    def test_write_csv_file_handles_special_characters(self, tmp_path):
        """Test CSV escaping for commas, quotes, and newlines."""
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Project with, comma",
                project_task='Task with "quotes"'
            )
        ]

        gui = TimesheetGUI()
        gui.rows = rows

        output_file = tmp_path / "test_special.csv"
        gui._write_csv_file(str(output_file))

        # Reload and verify escaping worked
        reloaded = load_csv(str(output_file))
        assert len(reloaded) == 1
        assert reloaded[0].project_name == "Project with, comma"
        assert reloaded[0].project_task == 'Task with "quotes"'

    def test_write_csv_file_uses_utf8_encoding(self, tmp_path):
        """Test that UTF-8 encoding is preserved."""
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Prøjéct Ñamé",  # Non-ASCII characters
                project_task="Täsk 日本語"     # Mixed scripts
            )
        ]

        gui = TimesheetGUI()
        gui.rows = rows

        output_file = tmp_path / "test_utf8.csv"
        gui._write_csv_file(str(output_file))

        # Reload and verify
        reloaded = load_csv(str(output_file))
        assert len(reloaded) == 1
        assert reloaded[0].project_name == "Prøjéct Ñamé"
        assert reloaded[0].project_task == "Täsk 日本語"

    def test_write_csv_file_empty_data_raises_error(self, tmp_path):
        """Test that writing with no data raises an error."""
        gui = TimesheetGUI()
        gui.rows = []

        output_file = tmp_path / "test_empty.csv"

        with pytest.raises(ValueError, match="No data to save"):
            gui._write_csv_file(str(output_file))

    @pytest.mark.skipif(sys.platform == 'win32', reason="Permission testing is unreliable on Windows")
    def test_write_csv_file_permission_error_handling(self, tmp_path):
        """Test handling of I/O errors during file writing."""
        import os

        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]

        gui = TimesheetGUI()
        gui.rows = rows

        # Try to write to a directory (not a file) - should raise error
        invalid_path = str(tmp_path)

        # Should raise some kind of I/O error
        with pytest.raises((OSError, IOError, PermissionError, IsADirectoryError)):
            gui._write_csv_file(invalid_path)


class TestDownloadEditSaveWorkflow:
    """Integration tests for template download → edit → save workflow."""

    def test_generated_template_can_be_edited_and_saved(self, tmp_path):
        """Test that a generated CSV template can be edited and saved."""
        # Simulate a CSV generated by template download
        csv_content = """project_number,project_name,project_task,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,TD_Academy_Simulator_Transition,01 - Unspecified,0,0,0,0,0,0,0
8-26214-30-01,PR_Engine_Commissioning,01 - Unspecified,0,0,0,0,0,0,0"""

        csv_file = tmp_path / "downloaded_template.csv"
        csv_file.write_text(csv_content)

        # Load in GUI
        gui = TimesheetGUI()
        gui.loadCSV(str(csv_file))

        # Edit data
        gui.rows[0].monday = 7.40
        gui.rows[1].friday = 3.5

        # Save
        output_file = tmp_path / "edited_template.csv"
        gui._write_csv_file(str(output_file))

        # Reload and verify edits persisted
        reloaded = load_csv(str(output_file))
        assert len(reloaded) == 2
        assert reloaded[0].monday == 7.40
        assert reloaded[1].friday == 3.5

    def test_legacy_template_can_be_edited_and_saved(self, tmp_path):
        """Test that old templates (with legacy headers) can be edited and saved.

        This ensures backward compatibility with templates downloaded before
        the header format was standardized.
        """
        # Simulate a CSV with legacy headers
        csv_content = """project_number,project_text,task,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,TD_Academy_Simulator,01 - Unspecified,0,0,0,0,0,0,0"""

        csv_file = tmp_path / "legacy_template.csv"
        csv_file.write_text(csv_content)

        # Load (should automatically map legacy headers)
        gui = TimesheetGUI()
        gui.loadCSV(str(csv_file))

        # Verify loaded correctly
        assert len(gui.rows) == 1
        assert gui.rows[0].project_name == "TD_Academy_Simulator"
        assert gui.rows[0].project_task == "01 - Unspecified"

        # Edit
        gui.rows[0].monday = 7.40

        # Save (should use canonical headers)
        output_file = tmp_path / "saved_from_legacy.csv"
        gui._write_csv_file(str(output_file))

        # Verify saved with canonical headers
        import csv
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == CSVSchema.CANONICAL_HEADERS

        # Reload and verify data
        reloaded = load_csv(str(output_file))
        assert reloaded[0].monday == 7.40
        assert reloaded[0].project_name == "TD_Academy_Simulator"

    def test_multiple_edit_save_cycles(self, tmp_path):
        """Test multiple cycles of load → edit → save."""
        # Initial CSV
        csv_content = """project_number,project_name,project_task,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,Test Project,Task,0,0,0,0,0,0,0"""

        csv_file = tmp_path / "multi_edit.csv"
        csv_file.write_text(csv_content)

        gui = TimesheetGUI()

        # Cycle 1: Load → Edit → Save
        gui.loadCSV(str(csv_file))
        gui.rows[0].monday = 7.40
        gui._write_csv_file(str(csv_file))

        # Cycle 2: Load → Edit → Save
        gui.loadCSV(str(csv_file))
        assert gui.rows[0].monday == 7.40
        gui.rows[0].tuesday = 7.40
        gui._write_csv_file(str(csv_file))

        # Cycle 3: Load → Verify
        gui.loadCSV(str(csv_file))
        assert gui.rows[0].monday == 7.40
        assert gui.rows[0].tuesday == 7.40

    def test_save_after_model_edit(self, tmp_path):
        """Test save workflow after editing through the model."""
        csv_content = """project_number,project_name,project_task,monday,tuesday,wednesday,thursday,friday,saturday,sunday
8-26214-10-42,Test,Task,0,0,0,0,0,0,0"""

        csv_file = tmp_path / "model_edit.csv"
        csv_file.write_text(csv_content)

        gui = TimesheetGUI()
        gui.loadCSV(str(csv_file))

        # Edit through model (simulating GUI edit)
        from PySide6.QtCore import Qt
        index = gui.table_model.index(0, 3)  # Monday
        success = gui.table_model.setData(index, "7.40", Qt.EditRole)
        assert success

        # Save
        output_file = tmp_path / "model_edit_saved.csv"
        gui._write_csv_file(str(output_file))

        # Verify
        reloaded = load_csv(str(output_file))
        assert reloaded[0].monday == 7.40
