"""
Tests for week utility functions.

This module tests the week range parsing, offset calculation,
and validation functions.
"""

import pytest
from timesheet_bot.week_utils import (
    parse_week_range,
    WeekRangeParseError,
    calculate_week_offset,
    validate_week_offset,
    parse_week_display
)


class TestParseWeekRange:
    """Tests for parse_week_range function."""

    def test_single_week(self):
        """Test parsing a single week number."""
        assert parse_week_range("48") == [48]

    def test_comma_separated(self):
        """Test parsing comma-separated weeks."""
        assert parse_week_range("48,49,50") == [48, 49, 50]

    def test_range(self):
        """Test parsing a range."""
        assert parse_week_range("48-50") == [48, 49, 50]

    def test_combined(self):
        """Test parsing combined format."""
        assert parse_week_range("48-50,52") == [48, 49, 50, 52]

    def test_unsorted_input(self):
        """Test that output is sorted even with unsorted input."""
        assert parse_week_range("50,48,49") == [48, 49, 50]

    def test_duplicates_removed(self):
        """Test that duplicates are removed."""
        assert parse_week_range("48,48,49,49") == [48, 49]

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        assert parse_week_range(" 48 , 49 , 50 ") == [48, 49, 50]

    def test_empty_string(self):
        """Test that empty string raises error."""
        with pytest.raises(WeekRangeParseError, match="cannot be empty"):
            parse_week_range("")

    def test_invalid_format(self):
        """Test that invalid format raises error."""
        with pytest.raises(WeekRangeParseError, match="Invalid"):
            parse_week_range("48-")

    def test_invalid_characters(self):
        """Test that invalid characters raise error."""
        with pytest.raises(WeekRangeParseError, match="Invalid"):
            parse_week_range("a,b,c")

    def test_week_out_of_range_low(self):
        """Test that week < 1 raises error."""
        with pytest.raises(WeekRangeParseError, match="out of range"):
            parse_week_range("0")

    def test_week_out_of_range_high(self):
        """Test that week > 53 raises error."""
        with pytest.raises(WeekRangeParseError, match="out of range"):
            parse_week_range("54")

    def test_range_reversed(self):
        """Test that reversed range raises error."""
        with pytest.raises(WeekRangeParseError, match="greater than end"):
            parse_week_range("50-48")


class TestCalculateWeekOffset:
    """Tests for calculate_week_offset function."""

    def test_same_week(self):
        """Test offset for same week."""
        assert calculate_week_offset(2025, 48, 2025, 48) == 0

    def test_forward_same_year(self):
        """Test forward offset within same year."""
        assert calculate_week_offset(2025, 48, 2025, 50) == 2

    def test_backward_same_year(self):
        """Test backward offset within same year."""
        assert calculate_week_offset(2025, 48, 2025, 46) == -2

    def test_across_year_boundary(self):
        """Test offset across year boundary."""
        # Week 52 of 2025 to Week 2 of 2026
        # Assuming 52 weeks per year: offset = (2026 * 52 + 2) - (2025 * 52 + 52) = 2
        offset = calculate_week_offset(2025, 52, 2026, 2)
        assert offset == 2


class TestValidateWeekOffset:
    """Tests for validate_week_offset function."""

    def test_within_forward_limit(self):
        """Test that offsets within forward limit are valid."""
        validate_week_offset(5, max_forward=10, max_backward=20)  # Should not raise

    def test_within_backward_limit(self):
        """Test that offsets within backward limit are valid."""
        validate_week_offset(-10, max_forward=10, max_backward=20)  # Should not raise

    def test_zero_offset(self):
        """Test that zero offset is valid."""
        validate_week_offset(0, max_forward=10, max_backward=20)  # Should not raise

    def test_exceeds_forward_limit(self):
        """Test that offset exceeding forward limit raises error."""
        with pytest.raises(ValueError, match="exceeds maximum forward"):
            validate_week_offset(11, max_forward=10, max_backward=20)

    def test_exceeds_backward_limit(self):
        """Test that offset exceeding backward limit raises error."""
        with pytest.raises(ValueError, match="exceeds maximum backward"):
            validate_week_offset(-21, max_forward=10, max_backward=20)


class TestParseWeekDisplay:
    """Tests for parse_week_display function."""

    def test_standard_format(self):
        """Test parsing standard format 'Week 48, 2025'."""
        year, week = parse_week_display("Week 48, 2025")
        assert year == 2025
        assert week == 48

    def test_no_comma_format(self):
        """Test parsing format without comma 'Week 48 2025'."""
        year, week = parse_week_display("Week 48 2025")
        assert year == 2025
        assert week == 48

    def test_short_format(self):
        """Test parsing short format 'W48 2025'."""
        year, week = parse_week_display("W48 2025")
        assert year == 2025
        assert week == 48

    def test_lowercase_week(self):
        """Test parsing with lowercase 'week'."""
        year, week = parse_week_display("week 48, 2025")
        assert year == 2025
        assert week == 48

    def test_invalid_week_number(self):
        """Test that invalid week number raises error."""
        with pytest.raises(ValueError, match="Invalid week number"):
            parse_week_display("Week 54, 2025")

    def test_invalid_year(self):
        """Test that invalid year raises error."""
        with pytest.raises(ValueError, match="Invalid year"):
            parse_week_display("Week 48, 1999")

    def test_unparseable_text(self):
        """Test that unparseable text raises error."""
        with pytest.raises(ValueError, match="Could not parse"):
            parse_week_display("Some random text")
