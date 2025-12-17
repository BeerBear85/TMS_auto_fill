"""
Tests for DOM mapping and selectors.

These tests use Playwright to verify that our selectors work correctly
with synthetic HTML that mimics the TMS structure.
"""

import pytest
from playwright.sync_api import sync_playwright, Page

from timesheet_bot.selectors import TMSSelectors


# Minimal HTML fixture that mimics the TMS table structure
MINIMAL_TMS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Test TMS</title>
</head>
<body>
    <table mat-table class="mat-table cdk-table">
        <thead>
            <tr mat-header-row class="mat-header-row">
                <th class="cdk-column-Project">Project</th>
                <th class="cdk-column-Monday">Monday</th>
                <th class="cdk-column-Tuesday">Tuesday</th>
            </tr>
        </thead>
        <tbody>
            <tr mat-row class="mat-row cdk-row">
                <td class="mat-cell cdk-cell cdk-column-Project">8-26214-10-42</td>
                <td class="mat-cell cdk-column-Monday">
                    <input type="text" name="monday" class="dayField" id="0-0">
                </td>
                <td class="mat-cell cdk-column-Tuesday">
                    <input type="text" name="tuesday" class="dayField" id="0-1">
                </td>
            </tr>
            <tr mat-row class="mat-row cdk-row">
                <td class="mat-cell cdk-cell cdk-column-Project">8-26214-30-01</td>
                <td class="mat-cell cdk-column-Monday">
                    <input type="text" name="monday" class="dayField" id="1-0">
                </td>
                <td class="mat-cell cdk-column-Tuesday">
                    <input type="text" name="tuesday" class="dayField" id="1-1">
                </td>
            </tr>
            <tr mat-row class="mat-row cdk-row">
                <td class="mat-cell cdk-cell cdk-column-Project">8-26245-04-01</td>
                <td class="mat-cell cdk-column-Monday">
                    <input type="text" name="monday" class="dayField" id="2-0" value="7.40">
                </td>
                <td class="mat-cell cdk-column-Tuesday">
                    <input type="text" name="tuesday" class="dayField" id="2-1">
                </td>
            </tr>
        </tbody>
    </table>
    <a class="btn-primary" href="#">Promark</a>
</body>
</html>
"""


@pytest.fixture(scope="module")
def browser():
    """Create a browser instance for tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


class TestTMSSelectors:
    """Tests for TMS selectors."""

    def test_table_selector(self, page: Page):
        """Test that the table selector finds the table."""
        page.set_content(MINIMAL_TMS_HTML)

        table = page.locator(TMSSelectors.TABLE)
        assert table.count() == 1

    def test_table_rows_selector(self, page: Page):
        """Test that the rows selector finds all data rows."""
        page.set_content(MINIMAL_TMS_HTML)

        rows = page.locator(TMSSelectors.TABLE_ROWS)
        assert rows.count() == 3

    def test_project_row_selector(self, page: Page):
        """Test that we can find a specific project row."""
        page.set_content(MINIMAL_TMS_HTML)

        # Test finding each project
        selector1 = TMSSelectors.get_project_row_selector("8-26214-10-42")
        row1 = page.locator(selector1)
        assert row1.count() == 1

        selector2 = TMSSelectors.get_project_row_selector("8-26214-30-01")
        row2 = page.locator(selector2)
        assert row2.count() == 1

        selector3 = TMSSelectors.get_project_row_selector("8-26245-04-01")
        row3 = page.locator(selector3)
        assert row3.count() == 1

    def test_project_row_selector_not_found(self, page: Page):
        """Test that non-existent projects return no results."""
        page.set_content(MINIMAL_TMS_HTML)

        selector = TMSSelectors.get_project_row_selector("9-99999-99-99")
        row = page.locator(selector)
        assert row.count() == 0

    def test_weekday_input_selector(self, page: Page):
        """Test that we can find input fields within a row."""
        page.set_content(MINIMAL_TMS_HTML)

        # Get the first project row
        row_selector = TMSSelectors.get_project_row_selector("8-26214-10-42")
        row = page.locator(row_selector).first

        # Find monday input within the row
        monday_selector = TMSSelectors.get_weekday_input_selector("monday")
        monday_input = row.locator(monday_selector)
        assert monday_input.count() == 1

        # Find tuesday input within the row
        tuesday_selector = TMSSelectors.get_weekday_input_selector("tuesday")
        tuesday_input = row.locator(tuesday_selector)
        assert tuesday_input.count() == 1

    def test_fill_input_field(self, page: Page):
        """Test that we can fill an input field."""
        page.set_content(MINIMAL_TMS_HTML)

        # Get the first project row
        row_selector = TMSSelectors.get_project_row_selector("8-26214-10-42")
        row = page.locator(row_selector).first

        # Fill monday input
        monday_selector = TMSSelectors.get_weekday_input_selector("monday")
        monday_input = row.locator(monday_selector).first

        monday_input.fill("7.40")

        # Verify the value
        value = monday_input.input_value()
        assert value == "7.40"

    def test_read_existing_value(self, page: Page):
        """Test that we can read an existing value from an input field."""
        page.set_content(MINIMAL_TMS_HTML)

        # The third project has a pre-filled monday value
        row_selector = TMSSelectors.get_project_row_selector("8-26245-04-01")
        row = page.locator(row_selector).first

        monday_selector = TMSSelectors.get_weekday_input_selector("monday")
        monday_input = row.locator(monday_selector).first

        value = monday_input.input_value()
        assert value == "7.40"

    def test_clear_input_field(self, page: Page):
        """Test that we can clear an input field."""
        page.set_content(MINIMAL_TMS_HTML)

        # The third project has a pre-filled monday value
        row_selector = TMSSelectors.get_project_row_selector("8-26245-04-01")
        row = page.locator(row_selector).first

        monday_selector = TMSSelectors.get_weekday_input_selector("monday")
        monday_input = row.locator(monday_selector).first

        # Clear the field
        monday_input.clear()

        # Verify it's empty
        value = monday_input.input_value()
        assert value == ""

    def test_promark_button_selector(self, page: Page):
        """Test that we can find the Promark button."""
        page.set_content(MINIMAL_TMS_HTML)

        button = page.locator(TMSSelectors.PROMARK_BUTTON)
        assert button.count() == 1

        # Verify it has the correct text
        text = button.inner_text()
        assert "Promark" in text

    def test_multiple_projects_same_prefix(self, page: Page):
        """Test that selectors distinguish between similar project numbers."""
        # This ensures "8-26214-10-42" doesn't match "8-26214-10-43"
        html = """
        <!DOCTYPE html>
        <html><body>
        <table mat-table class="mat-table">
            <tbody>
                <tr mat-row class="mat-row cdk-row">
                    <td class="cdk-column-Project">8-26214-10-42</td>
                    <td><input name="monday" class="dayField" id="0-0"></td>
                </tr>
                <tr mat-row class="mat-row cdk-row">
                    <td class="cdk-column-Project">8-26214-10-43</td>
                    <td><input name="monday" class="dayField" id="1-0"></td>
                </tr>
            </tbody>
        </table>
        </body></html>
        """
        page.set_content(html)

        # These should each find exactly one row
        selector1 = TMSSelectors.get_project_row_selector("8-26214-10-42")
        assert page.locator(selector1).count() == 1

        selector2 = TMSSelectors.get_project_row_selector("8-26214-10-43")
        assert page.locator(selector2).count() == 1

        # Verify they're different rows by checking input IDs
        row1 = page.locator(selector1).first
        input1 = row1.locator('input[name="monday"]')
        assert input1.get_attribute("id") == "0-0"

        row2 = page.locator(selector2).first
        input2 = row2.locator('input[name="monday"]')
        assert input2.get_attribute("id") == "1-0"


class TestSelectorHelpers:
    """Tests for selector helper methods."""

    def test_get_weekday_input_selector(self):
        """Test weekday input selector generation."""
        assert TMSSelectors.get_weekday_input_selector("monday") == 'input[name="monday"].dayField'
        assert TMSSelectors.get_weekday_input_selector("friday") == 'input[name="friday"].dayField'

    def test_weekdays_list(self):
        """Test that WEEKDAYS contains all days."""
        expected = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        assert TMSSelectors.WEEKDAYS == expected


class TestTableExtraction:
    """Tests for extracting project data from table."""

    def test_extract_project_data_with_columns(self, page: Page):
        """Test extracting project data when columns have proper names."""
        # Extended HTML with project details
        html_with_projects = """
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Test TMS</title></head>
        <body>
            <table mat-table class="mat-table cdk-table">
                <tbody>
                    <tr mat-row class="mat-row cdk-row">
                        <td class="mat-cell cdk-cell cdk-column-Project">8-26214-10-42</td>
                        <td class="mat-cell cdk-cell cdk-column-ProjectText">TD_Academy_Simulator_Transition</td>
                        <td class="mat-cell cdk-cell cdk-column-Task">01 - Unspecified</td>
                        <td class="mat-cell cdk-column-Monday">
                            <input type="text" name="monday" class="dayField" id="0-0">
                        </td>
                    </tr>
                    <tr mat-row class="mat-row cdk-row">
                        <td class="mat-cell cdk-cell cdk-column-Project">8-26214-30-01</td>
                        <td class="mat-cell cdk-cell cdk-column-ProjectText">PR_Engine Commissioning</td>
                        <td class="mat-cell cdk-cell cdk-column-Task">02 - Development</td>
                        <td class="mat-cell cdk-column-Monday">
                            <input type="text" name="monday" class="dayField" id="1-0">
                        </td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        page.set_content(html_with_projects)

        # Get all rows
        rows = page.locator(TMSSelectors.TABLE_ROWS).all()
        assert len(rows) == 2

        # Extract first project
        row1 = rows[0]
        project_number1 = row1.locator('td.cdk-column-Project').first.text_content().strip()
        project_text1 = row1.locator('td.cdk-column-ProjectText').first.text_content().strip()
        task1 = row1.locator('td.cdk-column-Task').first.text_content().strip()

        assert project_number1 == "8-26214-10-42"
        assert project_text1 == "TD_Academy_Simulator_Transition"
        assert task1 == "01 - Unspecified"

        # Extract second project
        row2 = rows[1]
        project_number2 = row2.locator('td.cdk-column-Project').first.text_content().strip()
        project_text2 = row2.locator('td.cdk-column-ProjectText').first.text_content().strip()
        task2 = row2.locator('td.cdk-column-Task').first.text_content().strip()

        assert project_number2 == "8-26214-30-01"
        assert project_text2 == "PR_Engine Commissioning"
        assert task2 == "02 - Development"

    def test_extract_project_data_without_column_names(self, page: Page):
        """Test extracting project data when columns don't have specific names (fallback strategy)."""
        # HTML without specific column names - relies on cell position
        html_no_columns = """
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Test TMS</title></head>
        <body>
            <table mat-table class="mat-table cdk-table">
                <tbody>
                    <tr mat-row class="mat-row cdk-row">
                        <td class="mat-cell cdk-cell">8-26214-10-42</td>
                        <td class="mat-cell cdk-cell">TD_Academy_Simulator_Transition</td>
                        <td class="mat-cell cdk-cell">01 - Unspecified</td>
                        <td class="mat-cell"><input type="text" name="monday" class="dayField"></td>
                    </tr>
                    <tr mat-row class="mat-row cdk-row">
                        <td class="mat-cell cdk-cell">8-26245-04-01</td>
                        <td class="mat-cell cdk-cell">CW_Administration</td>
                        <td class="mat-cell cdk-cell">65 - Absence</td>
                        <td class="mat-cell"><input type="text" name="monday" class="dayField"></td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        page.set_content(html_no_columns)

        # Get all rows and cells
        rows = page.locator(TMSSelectors.TABLE_ROWS).all()
        assert len(rows) == 2

        # Row 1: Test fallback extraction
        row1 = rows[0]
        cells1 = row1.locator('td').all()

        # Project number is in first cell
        project_number1 = cells1[0].text_content().strip()
        assert project_number1 == "8-26214-10-42"

        # Project text should be found by heuristic (has underscores, longer text)
        project_text1 = cells1[1].text_content().strip()
        assert project_text1 == "TD_Academy_Simulator_Transition"
        assert len(project_text1) > 10  # Passes the length heuristic
        assert '_' in project_text1  # Passes the underscore heuristic

        # Task should be found by pattern matching (digits followed by hyphen)
        task1 = cells1[2].text_content().strip()
        assert task1 == "01 - Unspecified"
        import re
        assert re.match(r'^\d+\s*[-–]\s*.+', task1)  # Matches pattern

        # Row 2: Different project
        row2 = rows[1]
        cells2 = row2.locator('td').all()

        project_number2 = cells2[0].text_content().strip()
        project_text2 = cells2[1].text_content().strip()
        task2 = cells2[2].text_content().strip()

        assert project_number2 == "8-26245-04-01"
        assert project_text2 == "CW_Administration"  # Passes length heuristic
        assert task2 == "65 - Absence"  # Matches task pattern
