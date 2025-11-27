"""
DOM selectors for the Timesheet Management System.

This module defines all the selectors needed to interact with the TMS web interface.
Selectors are based on the static HTML snapshot in /example/Timesheet Management System.html

IMPORTANT: These selectors are designed for the live Angular application.
If the DOM structure changes, this module will need to be updated.
"""

from typing import Dict


class TMSSelectors:
    """
    Centralized selectors for TMS DOM elements.

    All selectors use Playwright locator syntax.
    """

    # Main table selector
    # The table uses Angular Material components
    TABLE = 'table[mat-table]'

    # Table rows
    # Each project row has class "mat-row cdk-row"
    # We use tbody to skip header/footer rows
    TABLE_ROWS = 'tbody tr[mat-row]'

    # Save button (appears after data entry)
    # The "Save" button appears dynamically after filling data
    SAVE_BUTTON = 'button:has-text("Save")'

    # Alternative save button selectors
    SAVE_BUTTON_ALT = 'a:has-text("Save")'
    SAVE_BUTTON_ALT2 = 'button.btn:has-text("Save")'

    # Submit button
    # The "Promark" button is a link with specific text
    PROMARK_BUTTON = 'a:has-text("Promark")'

    # Alternative selector for Promark button
    PROMARK_BUTTON_ALT = 'a.btn-primary:has-text("Promark")'

    # Week navigation elements
    # Week display showing current week (e.g., "Week 48, 2025")
    # Multiple possible selectors for week display
    WEEK_DISPLAY = '.week-display, .week-selector, [class*="week"], h1, h2, h3'

    # Week navigation arrows
    # Left arrow (previous week)
    WEEK_ARROW_LEFT = 'button:has([class*="arrow-left"]), button:has([class*="prev"]), a:has([class*="arrow-left"]), a:has([class*="prev"]), [class*="arrow-left"], [class*="prev"]'

    # Right arrow (next week)
    WEEK_ARROW_RIGHT = 'button:has([class*="arrow-right"]), button:has([class*="next"]), a:has([class*="arrow-right"]), a:has([class*="next"]), [class*="arrow-right"], [class*="next"]'

    # Weekday column names (as they appear in the DOM)
    WEEKDAYS = [
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday'
    ]

    @staticmethod
    def get_project_row_selector(project_number: str) -> str:
        """
        Get selector for a table row matching a specific project number.

        Strategy:
        - Find a <tr> element with mat-row class
        - That contains a <td> with the project column class
        - That has exact text matching the project number

        Args:
            project_number: The project number to match (e.g., "8-26214-10-42")

        Returns:
            Playwright selector string

        Example:
            >>> TMSSelectors.get_project_row_selector("8-26214-10-42")
            'tr.mat-row:has(td.cdk-column-Project:has-text("8-26214-10-42"))'
        """
        # Use text-based matching for robustness
        # The :has-text() selector will match if the element contains the text
        # We use the Project column class to be more specific
        return f'tr.mat-row:has(td.cdk-column-Project:has-text("{project_number}"))'

    @staticmethod
    def get_weekday_input_selector(weekday: str) -> str:
        """
        Get selector for a weekday input field within a row context.

        Args:
            weekday: Day name (lowercase: monday, tuesday, etc.)

        Returns:
            Relative selector for the input field within a row

        Example:
            >>> TMSSelectors.get_weekday_input_selector("monday")
            'input[name="monday"].dayField'
        """
        # Inputs have name attribute matching weekday and class "dayField"
        return f'input[name="{weekday}"].dayField'

    @staticmethod
    def get_cell_selector(project_number: str, weekday: str) -> str:
        """
        Get combined selector for a specific cell (project + weekday).

        This combines the row selector and input selector.

        Args:
            project_number: The project number
            weekday: The weekday name (lowercase)

        Returns:
            Full selector string

        Note:
            This returns a selector for the row. You should:
            1. Locate the row using this selector
            2. Then locate the input within that row
        """
        row_selector = TMSSelectors.get_project_row_selector(project_number)
        input_selector = TMSSelectors.get_weekday_input_selector(weekday)
        # Return just the row selector - the input will be found within it
        return row_selector


# Selector strategies explained:
#
# 1. PROJECT ROW DETECTION:
#    - We use tr.mat-row to find table rows (Angular Material structure)
#    - We use :has(td.cdk-column-Project:has-text("...")) to match the exact project
#    - This is text-based and robust to row reordering
#
# 2. WEEKDAY INPUT FIELDS:
#    - Within each row, inputs have name="monday", name="tuesday", etc.
#    - They also have class="dayField" which we use for additional specificity
#    - We search for these inputs WITHIN the matched row, not globally
#
# 3. SUBMIT BUTTON:
#    - The "Promark" button is an <a> tag with text "Promark"
#    - We use text-based matching: a:has-text("Promark")
#
# 4. ASSUMPTIONS:
#    - Project numbers are unique within the table
#    - Input fields use name attributes matching weekday names
#    - The DOM structure follows Angular Material patterns
#    - The table is already loaded when we interact with it
#
# 5. TROUBLESHOOTING:
#    - If selectors fail, inspect the live HTML at /example/Timesheet Management System.html
#    - Check if Angular has changed the class names or structure
#    - Verify that project numbers are exact matches (including formatting)
#    - Ensure the page has fully loaded before trying to interact


# Convenience selector map for programmatic access
WEEKDAY_SELECTORS: Dict[str, str] = {
    day: TMSSelectors.get_weekday_input_selector(day)
    for day in TMSSelectors.WEEKDAYS
}
