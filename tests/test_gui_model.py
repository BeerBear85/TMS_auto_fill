"""
Unit tests for GUI model editing functionality.

Tests the TimesheetTableModel's editing capabilities, validation,
and dirty state tracking.
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QModelIndex
from timesheet_bot.gui import TimesheetTableModel
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


class TestTimesheetTableModelEditing:
    """Tests for table model editing functionality."""

    def test_model_flags_editable_cells(self):
        """Test that data cells return editable flags."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test Project",
                project_task="01 - Unspecified",
                monday=7.40
            )
        ]
        model.setRows(rows)

        # Test data cell (project name)
        index = model.index(0, 1)  # Row 0, Column 1 (project_name)
        flags = model.flags(index)
        assert flags & Qt.ItemIsEditable, "Data cells should be editable"
        assert flags & Qt.ItemIsEnabled
        assert flags & Qt.ItemIsSelectable

    def test_model_flags_readonly_totals_row(self):
        """Test that totals row is read-only."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test Project",
                project_task="01 - Unspecified"
            )
        ]
        model.setRows(rows)

        # Test totals row (last row)
        totals_row = len(rows)
        index = model.index(totals_row, 0)  # Totals row, any column
        flags = model.flags(index)
        assert not (flags & Qt.ItemIsEditable), "Totals row should not be editable"

    def test_model_flags_readonly_total_column(self):
        """Test that Total column is read-only."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test Project",
                project_task="01 - Unspecified"
            )
        ]
        model.setRows(rows)

        # Test Total column (column 10)
        index = model.index(0, 10)  # Row 0, Column 10 (Total)
        flags = model.flags(index)
        assert not (flags & Qt.ItemIsEditable), "Total column should not be editable"

    def test_setdata_project_number(self):
        """Test editing project number."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]
        model.setRows(rows)

        # Edit project number
        index = model.index(0, 0)  # Column 0: project_number
        result = model.setData(index, "8-99999-99-99", Qt.EditRole)

        assert result is True, "setData should return True for valid edit"
        assert model.rows[0].project_number == "8-99999-99-99"

    def test_setdata_project_number_empty_rejected(self):
        """Test that empty project number is rejected."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]
        model.setRows(rows)

        # Try to set empty project number
        index = model.index(0, 0)
        result = model.setData(index, "", Qt.EditRole)

        assert result is False, "Empty project number should be rejected"
        assert model.rows[0].project_number == "8-26214-10-42", "Original value should be unchanged"

    def test_setdata_project_name(self):
        """Test editing project name."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Old Name",
                project_task="Task"
            )
        ]
        model.setRows(rows)

        # Edit project name
        index = model.index(0, 1)  # Column 1: project_name
        result = model.setData(index, "New Project Name", Qt.EditRole)

        assert result is True
        assert model.rows[0].project_name == "New Project Name"

    def test_setdata_hours_valid(self):
        """Test editing hours with valid values."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task",
                monday=None
            )
        ]
        model.setRows(rows)

        # Edit Monday hours
        index = model.index(0, 3)  # Column 3: Monday
        result = model.setData(index, "7.40", Qt.EditRole)

        assert result is True
        assert model.rows[0].monday == 7.40

    def test_setdata_hours_negative_rejected(self):
        """Test that negative hours are rejected."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task",
                monday=5.0
            )
        ]
        model.setRows(rows)

        # Try to set negative hours
        index = model.index(0, 3)  # Monday
        result = model.setData(index, "-5.0", Qt.EditRole)

        assert result is False, "Negative hours should be rejected"
        assert model.rows[0].monday == 5.0, "Original value should be unchanged"

    def test_setdata_hours_invalid_rejected(self):
        """Test that invalid hours (non-numeric) are rejected."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task",
                monday=7.40
            )
        ]
        model.setRows(rows)

        # Try to set invalid hours
        index = model.index(0, 3)
        result = model.setData(index, "abc", Qt.EditRole)

        assert result is False, "Invalid hours should be rejected"
        assert model.rows[0].monday == 7.40, "Original value should be unchanged"

    def test_setdata_hours_empty(self):
        """Test that empty hours become None."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task",
                monday=7.40
            )
        ]
        model.setRows(rows)

        # Set empty string for hours
        index = model.index(0, 3)
        result = model.setData(index, "", Qt.EditRole)

        assert result is True
        assert model.rows[0].monday is None

    def test_setdata_whitespace_trimmed(self):
        """Test that whitespace is trimmed from text fields."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]
        model.setRows(rows)

        # Edit with extra whitespace
        index = model.index(0, 1)  # project_name
        result = model.setData(index, "  New Name  ", Qt.EditRole)

        assert result is True
        assert model.rows[0].project_name == "New Name", "Whitespace should be trimmed"

    def test_dirty_state_tracking(self):
        """Test dirty state detection."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]

        # Track signal emissions
        signal_received = []

        def on_dirty_changed(is_dirty):
            signal_received.append(is_dirty)

        model.dirty_state_changed.connect(on_dirty_changed)

        # Load data - should be clean
        model.setRows(rows)
        assert len(signal_received) == 1
        assert signal_received[0] is False, "Should emit False (clean) on load"
        assert model._is_dirty is False

        # Edit cell - should become dirty
        index = model.index(0, 1)
        model.setData(index, "Modified", Qt.EditRole)
        assert len(signal_received) == 2
        assert signal_received[1] is True, "Should emit True (dirty) after edit"
        assert model._is_dirty is True

        # Mark clean - should emit False
        model.mark_clean()
        assert len(signal_received) == 3
        assert signal_received[2] is False, "Should emit False after mark_clean"
        assert model._is_dirty is False

    def test_setrows_resets_dirty_state(self):
        """Test that setRows marks model as clean."""
        model = TimesheetTableModel()
        rows1 = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]
        model.setRows(rows1)

        # Make dirty
        index = model.index(0, 1)
        model.setData(index, "Modified", Qt.EditRole)
        assert model._is_dirty is True

        # Load new rows
        rows2 = [
            TimesheetRow(
                project_number="8-99999-99-99",
                project_name="New",
                project_task="New Task"
            )
        ]
        model.setRows(rows2)

        # Should be clean after setRows
        assert model._is_dirty is False
        assert model.rows[0].project_number == "8-99999-99-99"

    def test_mark_clean_preserves_current_state(self):
        """Test that mark_clean takes a snapshot of current state."""
        model = TimesheetTableModel()
        rows = [
            TimesheetRow(
                project_number="8-26214-10-42",
                project_name="Test",
                project_task="Task"
            )
        ]
        model.setRows(rows)

        # Edit
        index = model.index(0, 1)
        model.setData(index, "Modified", Qt.EditRole)
        assert model._is_dirty is True

        # Mark clean
        model.mark_clean()
        assert model._is_dirty is False

        # Edit again - should become dirty relative to new clean state
        model.setData(index, "Modified Again", Qt.EditRole)
        assert model._is_dirty is True

    def test_parse_hours_input_various_formats(self):
        """Test parsing various hour input formats."""
        model = TimesheetTableModel()

        # Valid numeric values
        assert model._parse_hours_input("7.40") == 7.40
        assert model._parse_hours_input("7") == 7.0
        assert model._parse_hours_input("0") == 0.0
        assert model._parse_hours_input("10.5") == 10.5

        # Empty values
        assert model._parse_hours_input("") is None
        assert model._parse_hours_input("   ") is None

        # Invalid values should raise
        with pytest.raises(ValueError):
            model._parse_hours_input("abc")

        with pytest.raises(ValueError):
            model._parse_hours_input("-5")
