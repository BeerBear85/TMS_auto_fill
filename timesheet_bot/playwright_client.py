"""
Playwright client for TMS automation.

This module handles all browser automation using Playwright,
including navigation, element interaction, and data filling.
"""

from typing import List, Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Locator, TimeoutError as PlaywrightTimeoutError

from .config import Config
from .models import (
    TimesheetRow,
    CellFillResult,
    ProjectFillResult,
    FillSummary
)
from .selectors import TMSSelectors
from .logging_utils import get_logger, log_step, log_error, log_warning, log_success


class TMSClient:
    """
    Playwright client for interacting with the Timesheet Management System.
    """

    def __init__(self, config: Config):
        """
        Initialize the TMS client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def start(self):
        """
        Start Playwright and launch browser.
        """
        log_step("Starting browser...", self.logger)

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.config.headless
        )

        self.context = self.browser.new_context()
        self.context.set_default_timeout(self.config.element_timeout)
        self.context.set_default_navigation_timeout(self.config.navigation_timeout)

        self.page = self.context.new_page()

        self.logger.debug(f"Browser launched (headless={self.config.headless})")

    def close(self):
        """
        Close browser and Playwright.
        """
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

        self.logger.debug("Browser closed")

    def navigate_to_tms(self):
        """
        Navigate to the TMS URL.

        Raises:
            Exception: If navigation fails
        """
        log_step(f"Navigating to {self.config.tms_url}...", self.logger)

        try:
            self.page.goto(self.config.tms_url, timeout=self.config.navigation_timeout)
            self.logger.debug("Navigation successful")
        except Exception as e:
            log_error(f"Failed to navigate: {e}", self.logger)
            raise

    def wait_for_manual_login(self):
        """
        Wait for the user to manually log in.

        This method displays a prompt and waits for the user to press ENTER
        after completing the login process.
        """
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("  MANUAL LOGIN REQUIRED")
        self.logger.info("=" * 70)
        self.logger.info("")
        self.logger.info("  Please complete the SSO login in the browser window.")
        self.logger.info("  Navigate to the week view where you see the timesheet table.")
        self.logger.info("")
        self.logger.info("  When ready, press ENTER to continue...")
        self.logger.info("=" * 70)

        input()

        log_step("Continuing after manual login...", self.logger)

    def wait_for_table(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for the timesheet table to be present on the page.

        Args:
            timeout: Timeout in milliseconds (uses config default if None)

        Returns:
            True if table is found, False otherwise
        """
        if timeout is None:
            timeout = self.config.element_timeout

        log_step("Waiting for timesheet table...", self.logger)

        try:
            self.page.locator(TMSSelectors.TABLE).wait_for(
                state='visible',
                timeout=timeout
            )
            log_success("Timesheet table found", self.logger)
            return True
        except PlaywrightTimeoutError:
            log_error("Timesheet table not found", self.logger)
            return False

    def fill_timesheet(self, rows: List[TimesheetRow]) -> FillSummary:
        """
        Fill the timesheet with data from CSV rows.

        Args:
            rows: List of timesheet rows to fill

        Returns:
            Summary of the fill operation
        """
        summary = FillSummary()
        summary.calculate_daily_totals(rows)

        self.logger.info("")
        self.logger.info(f"Filling {len(rows)} project(s)...")

        for i, row in enumerate(rows, 1):
            self.logger.info(f"\n[{i}/{len(rows)}] Processing: {row.project_number}")

            result = self._fill_project_row(row)
            summary.add_project_result(result)

            # Log result for this project
            if result.project_found:
                self.logger.info(
                    f"  ✓ Filled: {result.cells_filled}, "
                    f"Skipped: {result.cells_skipped}, "
                    f"Failed: {result.cells_failed}"
                )
            else:
                log_warning(f"  Project not found in table", self.logger)

        return summary

    def _fill_project_row(self, row: TimesheetRow) -> ProjectFillResult:
        """
        Fill a single project row.

        Args:
            row: Timesheet row data

        Returns:
            Result of filling this project
        """
        result = ProjectFillResult(project_number=row.project_number)

        # Try to find the project row
        try:
            row_locator = self._find_project_row(row.project_number)
            if row_locator is None:
                result.project_found = False
                result.error = "Project row not found in table"
                return result

            self.logger.debug(f"Found project row for {row.project_number}")

        except Exception as e:
            result.project_found = False
            result.error = str(e)
            log_error(f"Error finding project row: {e}", self.logger)
            return result

        # Fill each weekday
        for weekday in TMSSelectors.WEEKDAYS:
            value = row.get_weekday_value(weekday)

            # Skip if no value specified in CSV
            if value is None:
                continue

            cell_result = self._fill_cell(
                row_locator,
                row.project_number,
                weekday,
                value
            )

            result.cell_results.append(cell_result)

            if cell_result.success:
                result.cells_filled += 1
            elif cell_result.skipped:
                result.cells_skipped += 1
            else:
                result.cells_failed += 1

        return result

    def _find_project_row(self, project_number: str) -> Optional[Locator]:
        """
        Find a project row by project number.

        Args:
            project_number: Project number to find

        Returns:
            Locator for the row, or None if not found
        """
        try:
            selector = TMSSelectors.get_project_row_selector(project_number)
            row_locator = self.page.locator(selector).first

            # Check if the row exists
            count = row_locator.count()
            if count == 0:
                self.logger.debug(f"No row found for project {project_number}")
                return None

            return row_locator

        except Exception as e:
            self.logger.debug(f"Error finding project row: {e}")
            return None

    def _fill_cell(
        self,
        row_locator: Locator,
        project_number: str,
        weekday: str,
        value: float
    ) -> CellFillResult:
        """
        Fill a single cell with a value.

        Args:
            row_locator: Locator for the project row
            project_number: Project number (for logging)
            weekday: Weekday name
            value: Hours value to fill

        Returns:
            Result of filling this cell
        """
        result = CellFillResult(
            project_number=project_number,
            weekday=weekday,
            value=value,
            success=False
        )

        try:
            # Find the input field within the row
            input_selector = TMSSelectors.get_weekday_input_selector(weekday)
            input_locator = row_locator.locator(input_selector).first

            # Check if input exists
            if input_locator.count() == 0:
                result.error = f"Input field for {weekday} not found"
                log_warning(f"    {weekday}: field not found", self.logger)
                return result

            # Check if field already has a value
            current_value = input_locator.input_value()

            if current_value and current_value.strip():
                if self.config.no_overwrite:
                    result.skipped = True
                    self.logger.debug(
                        f"    {weekday}: skipped (has value '{current_value}')"
                    )
                    return result
                else:
                    # Clear the field before filling
                    input_locator.clear()
                    self.logger.debug(
                        f"    {weekday}: overwriting '{current_value}'"
                    )

            # Fill the value
            # Convert float to string, handling decimal separator
            value_str = str(value)

            input_locator.fill(value_str)

            # Verify the fill
            new_value = input_locator.input_value()
            if new_value:
                result.success = True
                self.logger.debug(f"    {weekday}: filled with {value}")
            else:
                result.error = "Fill verification failed"
                log_warning(f"    {weekday}: verification failed", self.logger)

            return result

        except Exception as e:
            result.error = str(e)
            log_warning(f"    {weekday}: error - {e}", self.logger)
            return result

    def click_promark(self) -> bool:
        """
        Click the "Promark" submit button.

        Returns:
            True if successful, False otherwise
        """
        log_step("Clicking Promark button...", self.logger)

        try:
            button = self.page.locator(TMSSelectors.PROMARK_BUTTON).first

            if button.count() == 0:
                # Try alternative selector
                button = self.page.locator(TMSSelectors.PROMARK_BUTTON_ALT).first

            if button.count() == 0:
                log_error("Promark button not found", self.logger)
                return False

            button.click()
            log_success("Promark button clicked", self.logger)

            # Wait a moment for the action to process
            self.page.wait_for_timeout(1000)

            return True

        except Exception as e:
            log_error(f"Failed to click Promark: {e}", self.logger)
            return False

    def take_screenshot(self, path: str):
        """
        Take a screenshot of the current page.

        Args:
            path: Path to save the screenshot
        """
        try:
            self.page.screenshot(path=path, full_page=True)
            self.logger.debug(f"Screenshot saved to {path}")
        except Exception as e:
            log_warning(f"Failed to take screenshot: {e}", self.logger)


def run_fill_operation(config: Config, rows: List[TimesheetRow]) -> FillSummary:
    """
    Execute the complete fill operation.

    Args:
        config: Application configuration
        rows: Timesheet rows to fill

    Returns:
        Summary of the operation

    Raises:
        Exception: If a critical error occurs
    """
    logger = get_logger()

    with TMSClient(config) as client:
        # Navigate to TMS
        client.navigate_to_tms()

        # Wait for manual login
        client.wait_for_manual_login()

        # Wait for table to load
        if not client.wait_for_table():
            raise Exception("Failed to find timesheet table after login")

        # Fill the timesheet
        summary = client.fill_timesheet(rows)

        # Auto-submit if requested
        if config.auto_submit:
            logger.info("")
            if not client.click_promark():
                log_warning("Auto-submit failed", logger)
        else:
            logger.info("")
            logger.info("Auto-submit disabled. Review the timesheet manually.")

        return summary
