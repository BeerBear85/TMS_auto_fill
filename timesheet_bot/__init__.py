"""
Timesheet Bot - Automated timesheet filling for TMS.

This package provides tools to automatically fill the Timesheet Management System
web application using data from CSV files.
"""

__version__ = '1.0.0'
__author__ = 'TMS Automation'

from .models import TimesheetRow, FillSummary
from .csv_loader import load_csv, CSVLoadError
from .config import Config
from .playwright_client import TMSClient, run_fill_operation

__all__ = [
    'TimesheetRow',
    'FillSummary',
    'load_csv',
    'CSVLoadError',
    'Config',
    'TMSClient',
    'run_fill_operation',
]
