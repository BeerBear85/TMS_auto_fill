"""
Playwright client for TMS automation.

This module handles all browser automation using Playwright,
including navigation, element interaction, and data filling.
"""

from typing import List, Optional, Dict
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
from .week_utils import parse_week_display, calculate_week_offset, validate_week_offset


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
            self.page.goto(
                self.config.tms_url,
                timeout=self.config.navigation_timeout,
                wait_until='domcontentloaded'
            )
            self.logger.debug("Navigation successful")
        except Exception as e:
            error_str = str(e)

            # Check for network-related errors
            if any(err in error_str for err in ['ERR_NAME_NOT_RESOLVED', 'ERR_CONNECTION', 'ERR_TUNNEL_CONNECTION_FAILED', 'net::']):
                log_error(f"Failed to navigate: {e}", self.logger)
                self.logger.error("")
                self.logger.error("=" * 70)
                self.logger.error("  NETWORK CONNECTION ERROR")
                self.logger.error("=" * 70)
                self.logger.error("")
                self.logger.error("  This error is often caused by:")
                self.logger.error("  - VPN/Proxy not connected (e.g., Zscaler, Cisco AnyConnect)")
                self.logger.error("  - VPN/Proxy not authenticated")
                self.logger.error("  - Network connectivity issues")
                self.logger.error("  - Firewall blocking the connection")
                self.logger.error("")
                self.logger.error("  Please ensure:")
                self.logger.error("  1. Your VPN/Proxy (e.g., Zscaler) is turned ON and authenticated")
                self.logger.error("  2. You can access the TMS website in your browser")
                self.logger.error(f"  3. The URL is correct: {self.config.tms_url}")
                self.logger.error("")
                self.logger.error("=" * 70)
                self.logger.error("")
            else:
                log_error(f"Failed to navigate: {e}", self.logger)

            raise

    def wait_for_manual_login(self):
        """
        Wait for the user to manually log in.

        For GUI mode (headless=False): Automatically detects login completion by polling
        for the timesheet table, with fallback to manual confirmation if needed.

        For CLI mode: Displays a prompt and waits for the user to press ENTER.
        """
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("  MANUAL LOGIN REQUIRED")
        self.logger.info("=" * 70)
        self.logger.info("")
        self.logger.info("  Please complete the SSO login in the browser window.")
        self.logger.info("  Navigate to the week view where you see the timesheet table.")
        self.logger.info("")

        # If running in GUI mode (headless=False), use automatic detection
        if not self.config.headless:
            self.logger.info("  Waiting for login to complete (monitoring for timesheet table)...")
            self.logger.info("=" * 70)

            # Poll for the timesheet table with timeout
            poll_interval = 2000  # Check every 2 seconds
            max_wait_time = 120000  # 120 seconds (2 minutes)
            elapsed = 0

            while elapsed < max_wait_time:
                try:
                    # Try to find the timesheet table
                    table = self.page.locator(TMSSelectors.TABLE)
                    table.wait_for(state='visible', timeout=poll_interval)

                    # If we get here, the table is visible - login complete!
                    log_success("Login detected! Timesheet table is now visible.", self.logger)
                    log_step("Continuing after manual login...", self.logger)
                    return

                except PlaywrightTimeoutError:
                    # Table not found yet, continue polling
                    elapsed += poll_interval
                    if elapsed % 10000 == 0:  # Log every 10 seconds
                        self.logger.debug(f"Still waiting for login... ({elapsed // 1000}s elapsed)")
                    continue

            # Timeout reached - table not detected automatically
            log_warning("Could not automatically detect login completion.", self.logger)
            self.logger.info("  If you have already logged in, the automation will continue shortly.")
            self.logger.info("  Otherwise, please complete the login now.")

            # Give a bit more time for slow loaders
            self.page.wait_for_timeout(5000)

        else:
            # CLI mode - use traditional input() method
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

    def detect_baseline_week(self) -> tuple[int, int]:
        """
        Detect the current week (baseline) from the DOM.

        Returns:
            Tuple of (year, week_number)

        Raises:
            Exception: If baseline week cannot be detected
        """
        log_step("Detecting baseline week from DOM...", self.logger)

        try:
            import re

            # Strategy 1: Try to find the week icon structure (time.icon with span.date)
            try:
                # Look for time elements with class "icon" that contain week information
                time_elements = self.page.locator('time.icon').all()

                for time_elem in time_elements:
                    # Check if this time element has the week structure
                    # (span.month containing "Week" and span.date containing the number)
                    month_span_text = time_elem.locator('span.month').text_content()

                    if month_span_text and 'week' in month_span_text.lower():
                        # Found the week display! Extract week number and year
                        week_num_text = time_elem.locator('span.date').text_content()
                        date_range_text = time_elem.locator('em').text_content()

                        # Extract week number (should be just digits, possibly with whitespace)
                        week_match = re.search(r'(\d+)', week_num_text)
                        if week_match:
                            week_num = int(week_match.group(1))

                            # Extract year from date range (e.g., "Nov 24 - Nov 30, 2025")
                            year_match = re.search(r'(\d{4})', date_range_text)
                            if year_match:
                                year = int(year_match.group(1))
                                self.logger.info(f"Detected baseline week: Week {week_num}, {year}")
                                return (year, week_num)

                self.logger.debug("Week icon structure not found, trying fallback...")

            except Exception as e:
                self.logger.debug(f"Week icon detection failed: {e}, trying fallback...")

            # Strategy 2: Fallback to text-based regex search (original approach)
            page_text = self.page.text_content('body')
            if page_text:
                patterns = [
                    r'[Ww]eek\s*(\d+)[,\s]+(\d{4})',
                    r'[Ww](\d+)\s+(\d{4})',
                    r'KW\s*(\d+)[,\s]+(\d{4})',  # German: Kalenderwoche
                ]

                for pattern in patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        week_num = int(match.group(1))
                        year = int(match.group(2))
                        self.logger.info(f"Detected baseline week: Week {week_num}, {year}")
                        return (year, week_num)

            # If we couldn't find it, raise an error with helpful message
            raise Exception(
                "Could not detect baseline week from DOM. "
                "Please ensure the week selector is visible on the page. "
                "The page may still be loading or the structure may have changed."
            )

        except Exception as e:
            log_error(f"Failed to detect baseline week: {e}", self.logger)
            raise

    def verify_current_week(self, expected_year: int, expected_week: int) -> bool:
        """
        Verify that the currently displayed week matches the expected week.

        Args:
            expected_year: Expected year
            expected_week: Expected week number

        Returns:
            True if the current week matches, False otherwise

        Raises:
            Exception: If verification fails critically
        """
        try:
            current_year, current_week = self.detect_baseline_week()

            if current_year == expected_year and current_week == expected_week:
                self.logger.debug(f"Week verification passed: Week {current_week}, {current_year}")
                return True
            else:
                log_error(
                    f"Week verification failed: Expected Week {expected_week}, {expected_year} "
                    f"but found Week {current_week}, {current_year}",
                    self.logger
                )
                return False

        except Exception as e:
            log_error(f"Week verification error: {e}", self.logger)
            raise

    def navigate_to_week(self, target_year: int, target_week: int,
                        baseline_year: int, baseline_week: int) -> bool:
        """
        Navigate to a specific week using the week arrow buttons.

        Args:
            target_year: Target year
            target_week: Target week number
            baseline_year: Baseline (current) year
            baseline_week: Baseline (current) week number

        Returns:
            True if navigation successful, False otherwise

        Raises:
            ValueError: If offset exceeds allowed bounds
            Exception: If navigation fails
        """
        # Calculate offset
        offset = calculate_week_offset(baseline_year, baseline_week, target_year, target_week)

        self.logger.info(
            f"Navigating from Week {baseline_week}, {baseline_year} "
            f"to Week {target_week}, {target_year} (offset: {offset:+d})"
        )

        # Validate offset is within bounds
        try:
            validate_week_offset(offset, max_forward=10, max_backward=20)
        except ValueError as e:
            log_error(str(e), self.logger)
            raise

        # If offset is 0, we're already on the target week
        if offset == 0:
            self.logger.info("Already on target week, no navigation needed")
            return True

        # Determine which arrow to click and how many times
        if offset > 0:
            # Navigate forward (right arrow)
            arrow_selector = TMSSelectors.WEEK_ARROW_RIGHT
            direction = "forward"
            clicks = offset
        else:
            # Navigate backward (left arrow)
            arrow_selector = TMSSelectors.WEEK_ARROW_LEFT
            direction = "backward"
            clicks = abs(offset)

        self.logger.info(f"Clicking {direction} arrow {clicks} time(s)...")

        try:
            for i in range(clicks):
                # Wait a bit for any dynamic content to load
                self.page.wait_for_timeout(1000)

                # Find the arrow button
                arrow_locator = self.page.locator(arrow_selector)

                if arrow_locator.count() == 0:
                    raise Exception(f"Week navigation arrow ({direction}) not found")

                # Click the first arrow button
                arrow_locator.first.click()

                # Wait for the page to update
                self.page.wait_for_timeout(500)  # 500ms wait between clicks

                self.logger.debug(f"  Click {i+1}/{clicks} completed")

            # Verify we reached the target week
            if not self.verify_current_week(target_year, target_week):
                raise Exception(
                    f"Navigation verification failed: did not reach Week {target_week}, {target_year}"
                )

            log_success(f"Successfully navigated to Week {target_week}, {target_year}", self.logger)
            return True

        except Exception as e:
            log_error(f"Navigation failed: {e}", self.logger)
            raise

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

    def click_save(self) -> bool:
        """
        Click the "Save" button (appears after data entry).

        The Save button only appears dynamically after data has been entered,
        so this method waits for it to become visible before clicking.

        Returns:
            True if successful, False otherwise
        """
        log_step("Waiting for Save button to appear...", self.logger)

        try:
            # Wait for the Save button to appear (it shows after data entry)
            # Try primary selector first
            button = self.page.locator(TMSSelectors.SAVE_BUTTON).first

            try:
                button.wait_for(state='visible', timeout=5000)  # 5 second wait
                self.logger.debug("Save button found")
            except PlaywrightTimeoutError:
                # Try alternative selectors
                self.logger.debug("Trying alternative Save button selectors...")
                button = self.page.locator(TMSSelectors.SAVE_BUTTON_ALT).first

                try:
                    button.wait_for(state='visible', timeout=2000)
                except PlaywrightTimeoutError:
                    button = self.page.locator(TMSSelectors.SAVE_BUTTON_ALT2).first
                    button.wait_for(state='visible', timeout=2000)

            if button.count() == 0:
                log_error("Save button not found after waiting", self.logger)
                return False

            # Click the button
            log_step("Clicking Save button...", self.logger)
            button.click()
            self.logger.debug("Save button clicked")

            # Wait for page reload after clicking Save
            # BUG FIX: TMS reloads/refreshes the page after save with a loading animation
            # Previous implementation incorrectly checked if button disappeared (it doesn't)
            # We need to wait for the reload to complete before the browser closes
            self.logger.debug("Waiting for page reload to complete...")

            try:
                # Strategy 1: Wait for navigation/reload to complete
                # Use wait_for_load_state to ensure page is fully loaded
                self.page.wait_for_load_state('networkidle', timeout=5000)
                self.logger.debug("Page reload detected and completed")
            except Exception as e:
                # If no reload detected, fallback to timeout
                # (TMS might do a soft refresh without full navigation)
                self.logger.debug(f"No page reload detected, using fallback wait: {e}")
                self.page.wait_for_timeout(3000)

            # Additional wait to ensure server-side processing completes
            self.page.wait_for_timeout(1000)

            # Optional: Verify save by checking if table is still present
            # This is a strong indicator that save was successful
            try:
                table = self.page.locator(TMSSelectors.TABLE).first
                if table.count() > 0:
                    self.logger.debug("Table still present after save (save likely succeeded)")
            except Exception as e:
                # Non-critical error - just log it
                self.logger.debug(f"Could not verify table presence: {e}")

            return True

        except PlaywrightTimeoutError:
            log_error("Save button did not appear (timeout)", self.logger)
            log_warning("Note: Save button only appears after data entry", self.logger)
            return False
        except Exception as e:
            log_error(f"Failed to click Save: {e}", self.logger)
            return False

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

    def extract_project_rows(self) -> List[Dict[str, str]]:
        """
        Extract project data from all visible rows in the timesheet table.

        Returns:
            List of dictionaries containing project_number, project_text, and task

        Raises:
            Exception: If table extraction fails
        """
        log_step("Extracting project data from table...", self.logger)

        projects = []

        try:
            # Find all table rows
            rows = self.page.locator(TMSSelectors.TABLE_ROWS).all()

            if len(rows) == 0:
                raise Exception("No table rows found")

            self.logger.info(f"Found {len(rows)} row(s) in table")

            for i, row in enumerate(rows, 1):
                try:
                    # Extract project number (required)
                    project_cell = row.locator('td.cdk-column-Project').first
                    if project_cell.count() == 0:
                        self.logger.debug(f"  Row {i}: Skipping - no project column found")
                        continue

                    project_number = project_cell.text_content().strip()
                    if not project_number:
                        self.logger.debug(f"  Row {i}: Skipping - empty project number")
                        continue

                    # Skip rows that look like totals/summaries
                    if 'total' in project_number.lower() or 'sum' in project_number.lower():
                        self.logger.debug(f"  Row {i}: Skipping summary row")
                        continue

                    # Get all cells in the row to analyze structure
                    all_cells = row.locator('td').all()

                    # Extract project text/name
                    # Strategy 1: Try known column name variations
                    project_text = ""
                    for col_name in ['ProjectText', 'ProjectName', 'Project_Text', 'Project_Name',
                                    'Description', 'Text', 'Name', 'Projecttext', 'projecttext']:
                        text_cell = row.locator(f'td.cdk-column-{col_name}').first
                        if text_cell.count() > 0:
                            project_text = text_cell.text_content().strip()
                            if project_text and project_text != project_number:
                                self.logger.debug(f"    Found project_text in column: cdk-column-{col_name}")
                                break

                    # Strategy 2: If not found, look for cells that contain text but aren't the project number
                    # and aren't input fields. The project text is typically in the 2nd or 3rd column.
                    if not project_text:
                        for idx, cell in enumerate(all_cells):
                            # Skip cells with input fields
                            if cell.locator('input').count() > 0:
                                continue

                            cell_text = cell.text_content().strip()

                            # Check if this looks like project text (not empty, not the project number)
                            if cell_text and cell_text != project_number:
                                # Check if it looks like a project name (has underscores or alphanumeric)
                                # and is not just a short code
                                if len(cell_text) > 3 and ('_' in cell_text or len(cell_text) > 10):
                                    project_text = cell_text
                                    self.logger.debug(f"    Found project_text in cell {idx}: {project_text[:30]}...")
                                    break

                    # Extract task
                    task = ""
                    for col_name in ['Task', 'Activity', 'TaskDescription', 'task', 'Tasktext']:
                        task_cell = row.locator(f'td.cdk-column-{col_name}').first
                        if task_cell.count() > 0:
                            task = task_cell.text_content().strip()
                            if task:
                                self.logger.debug(f"    Found task in column: cdk-column-{col_name}")
                                break

                    # Strategy 2 for task: Look for cells with task-like patterns (digits followed by text)
                    if not task:
                        import re
                        for idx, cell in enumerate(all_cells):
                            if cell.locator('input').count() > 0:
                                continue

                            cell_text = cell.text_content().strip()

                            # Check if it looks like a task (e.g., "01 - Unspecified", "65 - Absence")
                            if re.match(r'^\d+\s*[-–]\s*.+', cell_text):
                                task = cell_text
                                self.logger.debug(f"    Found task in cell {idx}: {task}")
                                break

                    # Create project data dictionary
                    # Use project_number as fallback only if absolutely nothing found
                    project_data = {
                        'project_number': project_number,
                        'project_text': project_text if project_text else project_number,
                        'task': task if task else '01 - Unspecified'
                    }

                    projects.append(project_data)
                    self.logger.debug(
                        f"  Row {i}: Extracted - {project_number} | "
                        f"{project_text[:30] if project_text else 'N/A'}... | {task[:20] if task else 'N/A'}..."
                    )

                except Exception as e:
                    log_warning(f"  Row {i}: Error extracting data - {e}", self.logger)
                    continue

            if not projects:
                raise Exception("No valid project rows could be extracted from table")

            log_success(f"Successfully extracted {len(projects)} project(s)", self.logger)
            return projects

        except Exception as e:
            log_error(f"Failed to extract project rows: {e}", self.logger)
            raise

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

    Supports filling multiple weeks if config.weeks is specified.

    Args:
        config: Application configuration
        rows: Timesheet rows to fill

    Returns:
        Summary of the operation

    Raises:
        Exception: If a critical error occurs

    Bug Fix (2025-12-17):
        Fixed issue where the last processed week was not saved properly when auto_submit
        was enabled. The bug occurred because:
        1. click_save() only waited 1.5 seconds after clicking the Save button
        2. No proper wait for TMS page reload after save
        3. Browser closed immediately after the last week, losing unsaved data

        TMS Save Behavior:
        - After clicking Save, TMS reloads/refreshes the page with a loading animation
        - The Save button does NOT disappear (remains visible)
        - Input values should persist in the DOM if save succeeded

        Fix:
        - Wait for page reload using wait_for_load_state('networkidle', timeout=5000)
        - Fallback to 3-second timeout if no reload detected (soft refresh)
        - Additional 1-second buffer to ensure server-side processing completes
        - Total wait time: ~5-6 seconds (sufficient for slow networks)
        - Added INFO-level logging: "Saving week X" and "Save completed for week X"
        - Verify table presence after save (optional validation)

        Reproduction:
        1. Run with --auto-submit and multiple weeks: --weeks 51,52
        2. Observe that week 51 is filled and saved
        3. Week 52 is filled and saved
        4. Previously: week 52 data would be lost due to browser closing before reload completed
        5. Now: week 52 data persists because we wait for reload to complete

        Regression test:
        - Manual: Run with --auto-submit --weeks 51,52 and verify both weeks are saved
        - Automated: Would require mocking the TMS system or using a test fixture
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

        # Detect baseline week
        logger.info("")
        baseline_year, baseline_week = client.detect_baseline_week()

        # Determine which weeks to process
        if config.weeks is not None and len(config.weeks) > 0:
            # Multi-week mode
            weeks_to_process = config.weeks
            logger.info(f"Multi-week mode: Processing {len(weeks_to_process)} week(s): {weeks_to_process}")
        else:
            # Single week mode (current week)
            weeks_to_process = [baseline_week]
            logger.info(f"Single week mode: Processing only Week {baseline_week}, {baseline_year}")

        # Overall summary (aggregates results from all weeks)
        overall_summary = FillSummary()
        overall_summary.calculate_daily_totals(rows)

        # Process each week
        for week_index, target_week in enumerate(weeks_to_process, 1):
            logger.info("")
            logger.info("=" * 70)

            # Determine target year
            # Use config.year if provided, otherwise assume same year as baseline
            if config.year is not None:
                target_year = config.year
            else:
                target_year = baseline_year

            logger.info(f"PROCESSING WEEK {week_index}/{len(weeks_to_process)}: Week {target_week}, {target_year}")
            logger.info("=" * 70)

            try:
                # Navigate to the target week if needed
                if target_week != baseline_week or target_year != baseline_year or week_index > 1:
                    # Get current week before navigation
                    current_year, current_week = client.detect_baseline_week()

                    client.navigate_to_week(
                        target_year=target_year,
                        target_week=target_week,
                        baseline_year=current_year,
                        baseline_week=current_week
                    )

                    # Wait for table to reload after navigation
                    if not client.wait_for_table():
                        raise Exception(f"Failed to find timesheet table for Week {target_week}")
                else:
                    logger.info(f"Already on Week {target_week}, {target_year}")

                # Fill the timesheet for this week
                week_summary = client.fill_timesheet(rows)

                # Aggregate results into overall summary
                overall_summary.total_projects += week_summary.total_projects
                overall_summary.projects_found += week_summary.projects_found
                overall_summary.projects_not_found += week_summary.projects_not_found
                overall_summary.total_cells_filled += week_summary.total_cells_filled
                overall_summary.total_cells_skipped += week_summary.total_cells_skipped
                overall_summary.total_cells_failed += week_summary.total_cells_failed
                overall_summary.missing_projects.extend(week_summary.missing_projects)
                overall_summary.project_results.extend(week_summary.project_results)

                # Auto-submit if requested (submit after each week)
                if config.auto_submit:
                    logger.info("")
                    logger.info(f"Saving week {target_week}...")
                    if not client.click_save():
                        # Fail-fast on submit failure
                        raise Exception(f"Auto-submit failed for Week {target_week}")
                    log_success(f"Save completed for week {target_week}", logger)

                logger.info("")
                log_success(f"Week {target_week} completed successfully", logger)

            except Exception as e:
                # Fail-fast: stop immediately on any error
                logger.info("")
                log_error(f"Failed to process Week {target_week}: {e}", logger)
                raise Exception(f"Operation failed at Week {target_week}: {e}")

        # Final summary
        if config.auto_submit:
            # Extra safety buffer after last save to ensure it fully propagates
            # before browser closes (especially important for GUI mode)
            logger.debug("Waiting for final save to fully propagate...")
            client.page.wait_for_timeout(2000)
        else:
            logger.info("")
            logger.info("Auto-submit disabled. Remember to click Save manually for each week.")

        return overall_summary
