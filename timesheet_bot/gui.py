"""
PySide6 GUI for the Timesheet Automation Tool.

This module provides a graphical interface for loading CSV files,
inspecting timesheet data, and running the automation.
"""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QAbstractItemView,
    QLineEdit,
    QLabel,
    QFileDialog,
    QMessageBox,
    QDialog,
    QProgressDialog,
    QHeaderView,
    QSpinBox,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QBrush

from .csv_loader import load_csv, CSVLoadError
from .models import TimesheetRow, FillSummary
from .week_utils import parse_week_range, WeekRangeParseError
from .config import Config
from .playwright_client import run_fill_operation
from .network_utils import check_tms_connectivity, is_vpn_proxy_error


class TimesheetTableModel(QAbstractTableModel):
    """
    Table model for displaying timesheet CSV data with totals row.

    Supports editing of project and weekday cells, with automatic dirty state tracking.
    """

    WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    TOTALS_BG_COLOR = QColor(180, 180, 180)  # Darker grey for totals
    ALTERNATE_BG_COLOR = QColor(245, 255, 245)  # Very subtle light-green for alternating rows/columns

    # Signal emitted when dirty state changes (has unsaved edits)
    dirty_state_changed = Signal(bool)

    def __init__(self, rows: Optional[List[TimesheetRow]] = None):
        super().__init__()
        self.rows = rows or []
        self._original_rows = []  # Deep copy for dirty tracking
        self._is_dirty = False
        self.headers = ['Project', 'Project Name', 'Project Task'] + self.WEEKDAYS + ['Total']

    def rowCount(self, parent=QModelIndex()):
        # Include one extra row for totals
        return len(self.rows) + 1 if self.rows else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row_idx = index.row()
        col = index.column()
        is_totals_row = (row_idx == len(self.rows))
        is_total_column = (col == 10)  # Total column is now at index 10

        # Background color role - darker grey for totals row and Total column
        if role == Qt.BackgroundRole:
            if is_totals_row or is_total_column:
                return QBrush(self.TOTALS_BG_COLOR)
            # Apply subtle light-green to every second row and column for readability
            if (row_idx % 2 == 1) or (col % 2 == 1):
                return QBrush(self.ALTERNATE_BG_COLOR)
            return None

        # Display role - show formatted data
        if role == Qt.DisplayRole:
            # Totals row
            if is_totals_row:
                return self._get_totals_data(col)

            # Regular data rows
            row = self.rows[row_idx]

            # Project number column
            if col == 0:
                return row.project_number

            # Project name column
            elif col == 1:
                return row.project_name

            # Project task column
            elif col == 2:
                return row.project_task

            # Weekday columns (3-9, was 1-7)
            elif 3 <= col <= 9:
                weekday = self.WEEKDAYS[col - 3].lower()
                value = row.get_weekday_value(weekday)
                return f"{value:.2f}" if value is not None else "0.00"

            # Total column (10, was 8)
            elif col == 10:
                return f"{row.total_hours():.2f}"

        # Edit role - return raw value for editing (preserves existing values)
        if role == Qt.EditRole:
            # Totals row is not editable
            if is_totals_row:
                return None

            # Regular data rows
            row = self.rows[row_idx]

            # Project number column
            if col == 0:
                return row.project_number

            # Project name column
            elif col == 1:
                return row.project_name

            # Project task column
            elif col == 2:
                return row.project_task

            # Weekday columns (3-9) - return raw numeric value or current formatted value
            elif 3 <= col <= 9:
                weekday = self.WEEKDAYS[col - 3].lower()
                value = row.get_weekday_value(weekday)
                # Return the value as string for the editor to display
                if value is not None:
                    # Return clean number (no trailing zeros if whole number)
                    if value == int(value):
                        return str(int(value))
                    return str(value)
                return "0"

            # Total column is not editable
            elif col == 10:
                return None

        return None

    def _get_totals_data(self, col: int) -> str:
        """
        Get data for the totals row.

        Args:
            col: Column index

        Returns:
            Formatted total string
        """
        if col == 0:
            return "Total"

        # Project name and task columns - leave empty
        elif col in (1, 2):
            return ""

        # Weekday columns (3-9, was 1-7)
        elif 3 <= col <= 9:
            weekday = self.WEEKDAYS[col - 3].lower()
            total = sum(
                row.get_weekday_value(weekday) or 0.0
                for row in self.rows
            )
            return f"{total:.2f}"

        # Total column (10, was 8)
        elif col == 10:
            grand_total = sum(row.total_hours() for row in self.rows)
            return f"{grand_total:.2f}"

        return ""

    def flags(self, index):
        """
        Return item flags for the given index.

        Makes data cells editable (except totals row and Total column).
        """
        if not index.isValid():
            return Qt.NoItemFlags

        row_idx = index.row()
        col = index.column()
        is_totals_row = (row_idx == len(self.rows))
        is_total_column = (col == 10)

        # Totals row and Total column are read-only
        if is_totals_row or is_total_column:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        # All other cells are editable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        """
        Set data for a cell (handles editing).

        Args:
            index: Model index
            value: New value
            role: Edit role

        Returns:
            True if edit succeeded, False otherwise
        """
        if role != Qt.EditRole or not index.isValid():
            return False

        row_idx = index.row()
        col = index.column()

        # Prevent editing totals row
        if row_idx >= len(self.rows):
            return False

        row = self.rows[row_idx]

        try:
            # Column 0: project_number
            if col == 0:
                if not value or not value.strip():
                    return False  # Cannot be empty
                row.project_number = value.strip()

            # Column 1: project_name
            elif col == 1:
                row.project_name = value.strip() if value else ""

            # Column 2: project_task
            elif col == 2:
                row.project_task = value.strip() if value else ""

            # Columns 3-9: weekdays
            elif 3 <= col <= 9:
                weekday = self.WEEKDAYS[col - 3].lower()
                parsed_value = self._parse_hours_input(value)
                setattr(row, weekday, parsed_value)

            else:
                return False

            # Emit dataChanged signal
            self.dataChanged.emit(index, index, [Qt.DisplayRole])

            # Update dirty state
            self._update_dirty_state()

            return True

        except ValueError:
            return False

    def _parse_hours_input(self, value: str) -> Optional[float]:
        """
        Parse hours input with validation.

        Args:
            value: Input string

        Returns:
            Parsed float value or None if empty

        Raises:
            ValueError: If value is invalid
        """
        if not value or not value.strip():
            return None

        try:
            hours = float(value.strip())
            if hours < 0:
                raise ValueError("Hours cannot be negative")
            return hours
        except (ValueError, TypeError):
            raise ValueError(f"Invalid hours value: {value}")

    def _update_dirty_state(self):
        """Check if model has unsaved changes and emit signal if changed."""
        import copy
        new_dirty = (self.rows != self._original_rows)

        if new_dirty != self._is_dirty:
            self._is_dirty = new_dirty
            self.dirty_state_changed.emit(new_dirty)

    def setRows(self, rows: List[TimesheetRow]):
        """
        Update the model with new rows and mark as clean.

        Args:
            rows: New list of timesheet rows
        """
        import copy
        self.beginResetModel()
        self.rows = rows
        self._original_rows = copy.deepcopy(rows)
        self._is_dirty = False
        self.endResetModel()
        self.dirty_state_changed.emit(False)

    def mark_clean(self):
        """Mark current state as clean (after save)."""
        import copy
        self._original_rows = copy.deepcopy(self.rows)
        self._is_dirty = False
        self.dirty_state_changed.emit(False)


class AutomationWorker(QThread):
    """
    Worker thread for running the automation in the background.
    """
    finished = Signal(FillSummary)
    error = Signal(str)

    def __init__(self, config: Config, rows: List[TimesheetRow]):
        super().__init__()
        self.config = config
        self.rows = rows

    def run(self):
        """Execute the automation."""
        try:
            summary = run_fill_operation(self.config, self.rows)
            self.finished.emit(summary)
        except Exception as e:
            self.error.emit(str(e))


class FetchTemplateWorker(QThread):
    """
    Worker thread for fetching template from TMS.
    """
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, config: Config, output_path: str):
        super().__init__()
        self.config = config
        self.output_path = output_path

    def run(self):
        """Execute the template fetch operation."""
        try:
            from .playwright_client import TMSClient
            from .csv_generator import generate_csv_template, CSVGeneratorError

            with TMSClient(self.config) as client:
                client.navigate_to_tms()
                client.wait_for_manual_login()

                if not client.wait_for_table():
                    raise Exception(
                        "Failed to find timesheet table after login.\n\n"
                        "Please ensure you:\n"
                        "1. Completed the SSO login\n"
                        "2. Navigated to the week view\n"
                        "3. Can see the timesheet table"
                    )

                projects_data = client.extract_project_rows()

                if not projects_data:
                    raise Exception(
                        "No projects found in the timesheet table.\n\n"
                        "The table may be empty or not loaded correctly."
                    )

                csv_path = generate_csv_template(
                    projects_data,
                    self.output_path,
                    force=True
                )

                self.finished.emit(str(csv_path))

        except CSVGeneratorError as e:
            self.error.emit(f"Failed to generate CSV template:\n\n{str(e)}")
        except Exception as e:
            error_str = str(e)
            network_error_keywords = ['ERR_NAME_NOT_RESOLVED', 'ERR_CONNECTION',
                                     'ERR_TUNNEL_CONNECTION_FAILED', 'net::']
            is_network_error = any(keyword in error_str for keyword in network_error_keywords)

            if is_network_error:
                message = (
                    f"Network Connection Error\n\n"
                    f"{error_str}\n\n"
                    f"This error is often caused by:\n"
                    f"• VPN/Proxy not connected (e.g., Zscaler, Cisco AnyConnect)\n"
                    f"• VPN/Proxy not authenticated\n"
                    f"• Network connectivity issues\n"
                    f"• Firewall blocking the connection\n\n"
                    f"Please ensure:\n"
                    f"1. Your VPN/Proxy (e.g., Zscaler) is turned ON and authenticated\n"
                    f"2. You can access the TMS website in your browser\n"
                    f"3. The URL is reachable"
                )
                self.error.emit(message)
            else:
                self.error.emit(f"Template fetch operation failed:\n\n{error_str}")


class TimesheetGUI(QMainWindow):
    """
    Main GUI window for the Timesheet Automation Tool.
    """

    def __init__(self, csv_path: Optional[str] = None):
        super().__init__()
        self.csv_path = csv_path
        self.rows: List[TimesheetRow] = []
        self.worker: Optional[AutomationWorker] = None
        self.fetch_worker: Optional[FetchTemplateWorker] = None

        self.initUI()

        # Load CSV if provided via CLI
        if self.csv_path:
            self.loadCSV(self.csv_path)

    def initUI(self):
        """Initialize the user interface."""
        self.setWindowTitle("Timesheet Automation")
        self.setGeometry(100, 100, 1000, 600)

        # Enable drag-and-drop
        self.setAcceptDrops(True)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # File info label
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.file_label)

        # Load CSV button
        self.load_button = QPushButton("Open File...")
        self.load_button.clicked.connect(self.openFileDialog)
        layout.addWidget(self.load_button)

        # Fetch template button
        self.fetch_button = QPushButton("Fetch current template from TMS")
        self.fetch_button.clicked.connect(self.fetchTemplateFromTMS)
        layout.addWidget(self.fetch_button)

        # Save buttons section
        save_layout = QHBoxLayout()

        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)  # Disabled until dirty
        self.save_button.clicked.connect(self.saveCSV)
        save_layout.addWidget(self.save_button)

        self.save_as_button = QPushButton("Save As...")
        self.save_as_button.setEnabled(False)  # Disabled until data loaded
        self.save_as_button.clicked.connect(self.saveCSVAs)
        save_layout.addWidget(self.save_as_button)

        save_layout.addStretch()
        layout.addLayout(save_layout)

        # Table view
        self.table_view = QTableView()
        self.table_model = TimesheetTableModel()
        self.table_view.setModel(self.table_model)

        # Configure table appearance and enable editing
        self.table_view.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.SelectedClicked |
            QAbstractItemView.EditKeyPressed
        )  # Enable editing
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_view.verticalHeader().setVisible(True)

        # Connect dirty state signal
        self.table_model.dirty_state_changed.connect(self.onDirtyStateChanged)

        layout.addWidget(self.table_view)

        # Week and year selection section
        week_layout = QHBoxLayout()
        week_label = QLabel("Weeks to fill:")
        week_label.setStyleSheet("font-size: 12px;")
        week_layout.addWidget(week_label)

        self.week_input = QLineEdit()
        self.week_input.setPlaceholderText("e.g., 48-50 or 48,49,50")
        self.week_input.setMaximumWidth(200)
        week_layout.addWidget(self.week_input)

        # Year input
        year_label = QLabel("Year:")
        year_label.setStyleSheet("font-size: 12px; margin-left: 20px;")
        week_layout.addWidget(year_label)

        self.year_input = QSpinBox()
        self.year_input.setRange(2000, 2100)
        self.year_input.setValue(datetime.now().year)
        self.year_input.setMaximumWidth(100)
        week_layout.addWidget(self.year_input)

        week_layout.addStretch()

        layout.addLayout(week_layout)

        # Buttons section
        button_layout = QHBoxLayout()

        self.validate_button = QPushButton("Validate input (dry run)")
        self.validate_button.clicked.connect(self.validateInput)
        button_layout.addWidget(self.validate_button)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.runAutomation)
        button_layout.addWidget(self.run_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def openFileDialog(self):
        """Open file dialog to select a CSV file."""
        # Warn if there are unsaved changes
        if self.table_model._is_dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening a new file?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                self.saveCSV()
                if self.table_model._is_dirty:
                    # Save failed or was cancelled
                    return
            elif reply == QMessageBox.Cancel:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self.loadCSV(file_path)

    def closeEvent(self, event):
        """Handle window close event."""
        if self.table_model._is_dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                self.saveCSV()
                if self.table_model._is_dirty:
                    # Save failed or was cancelled
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        event.accept()

    def loadCSV(self, file_path: str):
        """
        Load and display a CSV file.

        Args:
            file_path: Path to the CSV file
        """
        try:
            self.rows = load_csv(file_path)
            self.table_model.setRows(self.rows)
            self.csv_path = file_path

            # Enable Save As button
            self.save_as_button.setEnabled(True)

            # Update file label and window title
            file_name = Path(file_path).name
            self.file_label.setText(f"File: {file_name}")
            self.setWindowTitle(f"Timesheet Automation - {file_name}")

            # Show success message briefly
            QMessageBox.information(
                self,
                "Success",
                f"Loaded {len(self.rows)} project(s) from {file_name}"
            )

        except CSVLoadError as e:
            QMessageBox.critical(
                self,
                "CSV Load Error",
                f"Failed to load CSV file:\n\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Unexpected error loading CSV:\n\n{str(e)}"
            )

    def onDirtyStateChanged(self, is_dirty: bool):
        """Handle model dirty state changes."""
        # Enable Save button only if dirty AND we have a file path
        self.save_button.setEnabled(is_dirty and self.csv_path is not None)

        # Update window title to show unsaved changes
        title = "Timesheet Automation"
        if self.csv_path:
            file_name = Path(self.csv_path).name
            title += f" - {file_name}"
        if is_dirty:
            title += " *"
        self.setWindowTitle(title)

    def saveCSV(self):
        """Save changes to the current CSV file."""
        if not self.csv_path:
            # No file path, fallback to Save As
            self.saveCSVAs()
            return

        if not self.rows:
            QMessageBox.warning(self, "No Data", "No data to save.")
            return

        try:
            self._write_csv_file(self.csv_path)
            self.table_model.mark_clean()

            file_name = Path(self.csv_path).name
            QMessageBox.information(
                self,
                "Success",
                f"Saved {len(self.rows)} project(s) to {file_name}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save CSV file:\n\n{str(e)}"
            )

    def saveCSVAs(self):
        """Save data to a new CSV file."""
        if not self.rows:
            QMessageBox.warning(self, "No Data", "No data to save.")
            return

        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            self.csv_path if self.csv_path else "timesheet.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            self._write_csv_file(file_path)
            self.csv_path = file_path
            self.table_model.mark_clean()

            file_name = Path(file_path).name
            self.file_label.setText(f"File: {file_name}")
            self.setWindowTitle(f"Timesheet Automation - {file_name}")

            QMessageBox.information(
                self,
                "Success",
                f"Saved {len(self.rows)} project(s) to {file_name}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save CSV file:\n\n{str(e)}"
            )

    def _write_csv_file(self, file_path: str):
        """
        Write current rows to CSV file using canonical schema.

        Args:
            file_path: Path to write CSV file

        Raises:
            Exception: If write fails
        """
        import csv
        from .csv_schema import CSVSchema

        # Validate data
        if not self.rows:
            raise ValueError("No data to save")

        # Convert TimesheetRow objects to CSV dictionaries
        csv_rows = []
        for row in self.rows:
            csv_row = {
                CSVSchema.PROJECT_NUMBER: row.project_number,
                CSVSchema.PROJECT_NAME: row.project_name,
                CSVSchema.PROJECT_TASK: row.project_task,
                CSVSchema.MONDAY: str(row.monday) if row.monday is not None else '',
                CSVSchema.TUESDAY: str(row.tuesday) if row.tuesday is not None else '',
                CSVSchema.WEDNESDAY: str(row.wednesday) if row.wednesday is not None else '',
                CSVSchema.THURSDAY: str(row.thursday) if row.thursday is not None else '',
                CSVSchema.FRIDAY: str(row.friday) if row.friday is not None else '',
                CSVSchema.SATURDAY: str(row.saturday) if row.saturday is not None else '',
                CSVSchema.SUNDAY: str(row.sunday) if row.sunday is not None else '',
            }
            csv_rows.append(csv_row)

        # Write to file using CSVSchema standards
        try:
            with open(file_path, 'w', encoding=CSVSchema.ENCODING, newline=CSVSchema.NEWLINE) as f:
                writer = csv.DictWriter(f, fieldnames=CSVSchema.CANONICAL_HEADERS)
                writer.writeheader()
                writer.writerows(csv_rows)
        except PermissionError:
            raise Exception("Cannot write to file. File may be open in another program.")
        except OSError as e:
            raise Exception(f"File system error: {e}")

    def fetchTemplateFromTMS(self):
        """
        Fetch current template from TMS by opening browser and extracting projects.
        """
        # Warn if there are unsaved changes
        if self.table_model._is_dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before fetching a new template?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                self.saveCSV()
                if self.table_model._is_dirty:
                    # Save failed or was cancelled
                    return
            elif reply == QMessageBox.Cancel:
                return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template CSV",
            "TemplateInput.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        config = Config(
            csv_path=None,
            headless=False,
            verbose=False
        )

        self.fetch_worker = FetchTemplateWorker(config, file_path)
        self.fetch_worker.finished.connect(self.onFetchFinished)
        self.fetch_worker.error.connect(self.onFetchError)

        self.fetch_progress_dialog = QProgressDialog(
            "Fetching template from TMS...\n\n"
            "Please complete login in the browser window.\n"
            "The operation will continue automatically once you're logged in.",
            None,
            0,
            0,
            self
        )
        self.fetch_progress_dialog.setWindowTitle("Fetching Template")
        self.fetch_progress_dialog.setWindowModality(Qt.WindowModal)
        self.fetch_progress_dialog.setCancelButton(None)
        self.fetch_progress_dialog.show()

        self.fetch_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.validate_button.setEnabled(False)
        self.run_button.setEnabled(False)

        self.fetch_worker.start()

    def onFetchFinished(self, csv_path: str):
        """
        Handle fetch operation completion.

        Args:
            csv_path: Path to the saved CSV file
        """
        if hasattr(self, 'fetch_progress_dialog'):
            self.fetch_progress_dialog.close()

        self.fetch_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.validate_button.setEnabled(True)
        self.run_button.setEnabled(True)

        file_name = Path(csv_path).name
        QMessageBox.information(
            self,
            "Template Saved",
            f"Template saved successfully!\n\n"
            f"File: {file_name}\n"
            f"Path: {csv_path}\n\n"
            f"You can now edit it and then open it in this GUI."
        )

    def onFetchError(self, error_message: str):
        """
        Handle fetch operation error.

        Args:
            error_message: Error message
        """
        if hasattr(self, 'fetch_progress_dialog'):
            self.fetch_progress_dialog.close()

        self.fetch_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.validate_button.setEnabled(True)
        self.run_button.setEnabled(True)

        QMessageBox.critical(
            self,
            "Fetch Failed",
            error_message
        )

    def validateInput(self):
        """
        Validate CSV and week input without starting browser (dry run).
        """
        # Check if CSV is loaded
        if not self.rows:
            QMessageBox.warning(
                self,
                "No CSV Loaded",
                "Please load a CSV file first."
            )
            return

        # Validate week input
        week_text = self.week_input.text().strip()
        if not week_text:
            QMessageBox.warning(
                self,
                "No Weeks Specified",
                "Please enter week numbers to fill (e.g., 48-50 or 48,49,50)."
            )
            return

        try:
            weeks = parse_week_range(week_text)

            # Check network connectivity
            success, error_msg = check_tms_connectivity(
                Config().tms_url,  # Use default TMS URL from config
                timeout=10
            )

            if not success:
                # Connectivity check failed
                is_vpn_issue = is_vpn_proxy_error(error_msg)

                if is_vpn_issue:
                    message = (
                        f"Network Connectivity Check Failed\n\n"
                        f"{error_msg}\n\n"
                        f"This error is often caused by:\n"
                        f"• VPN/Proxy not connected (e.g., Zscaler, Cisco AnyConnect)\n"
                        f"• VPN/Proxy not authenticated\n"
                        f"• Network connectivity issues\n"
                        f"• Firewall blocking the connection\n\n"
                        f"Please ensure:\n"
                        f"1. Your VPN/Proxy (e.g., Zscaler) is turned ON and authenticated\n"
                        f"2. You can access the TMS website in your browser\n"
                        f"3. The URL is reachable: {Config().tms_url}"
                    )
                else:
                    message = (
                        f"Network Connectivity Check Failed\n\n"
                        f"{error_msg}\n\n"
                        f"Please check:\n"
                        f"1. Your internet connection is working\n"
                        f"2. The TMS server is accessible\n"
                        f"3. The URL is reachable: {Config().tms_url}"
                    )

                QMessageBox.critical(
                    self,
                    "Network Error",
                    message
                )
                return  # Don't show success dialog

            # Get year value
            year = self.year_input.value()

            # Show validation success with connectivity status
            QMessageBox.information(
                self,
                "Validation Successful",
                f"CSV: {len(self.rows)} project(s) loaded\n"
                f"Weeks: {weeks}\n"
                f"Year: {year}\n"
                f"Network: Connected to TMS ✓\n\n"
                f"Input is valid and ready to run."
            )

        except WeekRangeParseError as e:
            QMessageBox.critical(
                self,
                "Invalid Week Range",
                f"Invalid week specification:\n\n{str(e)}"
            )

    def runAutomation(self):
        """
        Run the automation with browser.
        """
        # Check if CSV is loaded
        if not self.rows:
            QMessageBox.warning(
                self,
                "No CSV Loaded",
                "Please load a CSV file first."
            )
            return

        # Parse week input
        week_text = self.week_input.text().strip()
        if not week_text:
            QMessageBox.warning(
                self,
                "No Weeks Specified",
                "Please enter week numbers to fill (e.g., 48-50 or 48,49,50)."
            )
            return

        try:
            weeks = parse_week_range(week_text)
        except WeekRangeParseError as e:
            QMessageBox.critical(
                self,
                "Invalid Week Range",
                f"Invalid week specification:\n\n{str(e)}"
            )
            return

        # Get year value
        year = self.year_input.value()

        # Create configuration
        config = Config(
            csv_path=self.csv_path,
            weeks=weeks,
            year=year,
            headless=False,  # Always headful for GUI
            auto_submit=True,   # GUI always saves after filling (BUG FIX: was False, causing data loss)
            no_overwrite=False,
            dry_run=False,
            verbose=False
        )

        # Validate config
        try:
            config.validate()
        except ValueError as e:
            QMessageBox.critical(
                self,
                "Configuration Error",
                f"Configuration is invalid:\n\n{str(e)}"
            )
            return

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Run",
            f"Ready to fill {len(self.rows)} project(s) for:\n"
            f"  Weeks: {weeks}\n"
            f"  Year: {year}\n\n"
            f"This will open a browser window.\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Run automation in worker thread
        self.worker = AutomationWorker(config, self.rows)
        self.worker.finished.connect(self.onAutomationFinished)
        self.worker.error.connect(self.onAutomationError)

        # Show progress dialog
        self.progress_dialog = QProgressDialog(
            "Running automation...\n\n"
            "Please complete login in the browser window.\n"
            "The automation will continue automatically once you're logged in.",
            None,  # No cancel button (fail-fast behavior)
            0,
            0,  # Indeterminate progress
            self
        )
        self.progress_dialog.setWindowTitle("Working")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

        # Disable buttons during run
        self.validate_button.setEnabled(False)
        self.run_button.setEnabled(False)

        # Start worker
        self.worker.start()

    def onAutomationFinished(self, summary: FillSummary):
        """
        Handle automation completion.

        Args:
            summary: Fill operation summary
        """
        # Close progress dialog
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

        # Re-enable buttons
        self.validate_button.setEnabled(True)
        self.run_button.setEnabled(True)

        # Check for errors
        if summary.total_cells_failed > 0 or summary.projects_not_found > 0:
            message = f"Automation completed with errors:\n\n"
            message += f"Projects found: {summary.projects_found}/{summary.total_projects}\n"
            message += f"Cells filled: {summary.total_cells_filled}\n"
            message += f"Cells failed: {summary.total_cells_failed}\n"
            message += f"Cells skipped: {summary.total_cells_skipped}\n"

            if summary.missing_projects:
                message += f"\nMissing projects:\n"
                for proj in summary.missing_projects[:5]:  # Show first 5
                    message += f"  - {proj}\n"
                if len(summary.missing_projects) > 5:
                    message += f"  ... and {len(summary.missing_projects) - 5} more\n"

            QMessageBox.warning(
                self,
                "Completed with Errors",
                message
            )
        else:
            # Success
            message = f"Automation completed successfully!\n\n"
            message += f"Projects filled: {summary.projects_found}\n"
            message += f"Cells filled: {summary.total_cells_filled}\n"
            message += f"Cells skipped: {summary.total_cells_skipped}\n"

            QMessageBox.information(
                self,
                "Success",
                message
            )

    def onAutomationError(self, error_message: str):
        """
        Handle automation error.

        Args:
            error_message: Error message
        """
        # Close progress dialog
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

        # Re-enable buttons
        self.validate_button.setEnabled(True)
        self.run_button.setEnabled(True)

        # Check for network-related errors and provide helpful hints
        network_error_keywords = ['ERR_NAME_NOT_RESOLVED', 'ERR_CONNECTION', 'ERR_TUNNEL_CONNECTION_FAILED', 'net::']
        is_network_error = any(keyword in error_message for keyword in network_error_keywords)

        if is_network_error:
            message = f"Network Connection Error\n\n"
            message += f"{error_message}\n\n"
            message += f"This error is often caused by:\n"
            message += f"• VPN/Proxy not connected (e.g., Zscaler, Cisco AnyConnect)\n"
            message += f"• VPN/Proxy not authenticated\n"
            message += f"• Network connectivity issues\n"
            message += f"• Firewall blocking the connection\n\n"
            message += f"Please ensure:\n"
            message += f"1. Your VPN/Proxy (e.g., Zscaler) is turned ON and authenticated\n"
            message += f"2. You can access the TMS website in your browser\n"
            message += f"3. The URL is reachable"
        else:
            message = f"The automation failed with an error:\n\n{error_message}"

        # Show error dialog
        QMessageBox.critical(
            self,
            "Automation Failed",
            message
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event for drag-and-drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event for drag-and-drop."""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith('.csv'):
                self.loadCSV(file_path)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid File",
                    "Please drop a CSV file."
                )


def main(csv_path: Optional[str] = None):
    """
    Main entry point for the GUI application.

    Args:
        csv_path: Optional CSV file path to load on startup
    """
    app = QApplication(sys.argv)
    window = TimesheetGUI(csv_path)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Timesheet Automation GUI')
    parser.add_argument('csv', nargs='?', help='CSV file to load on startup')
    args = parser.parse_args()

    main(args.csv)
