"""
Tests for CSV schema module.

This module tests the central CSV schema definition that ensures
consistency between CSV generation and loading.
"""

import pytest
from timesheet_bot.csv_schema import CSVSchema


class TestCSVSchemaConstants:
    """Tests for CSV schema constants."""

    def test_canonical_headers_order(self):
        """Test that canonical headers are in the correct order."""
        expected_headers = [
            'project_number',
            'project_name',
            'project_task',
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
            'sunday',
        ]
        assert CSVSchema.CANONICAL_HEADERS == expected_headers

    def test_legacy_aliases_defined(self):
        """Test that legacy aliases are properly defined."""
        assert CSVSchema.LEGACY_ALIASES['project_text'] == 'project_name'
        assert CSVSchema.LEGACY_ALIASES['task'] == 'project_task'

    def test_weekday_headers(self):
        """Test weekday headers helper method."""
        weekdays = CSVSchema.get_weekday_headers()
        expected_weekdays = [
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]
        assert weekdays == expected_weekdays

    def test_encoding_standard(self):
        """Test that encoding standard is UTF-8."""
        assert CSVSchema.ENCODING == 'utf-8'

    def test_delimiter_standard(self):
        """Test that delimiter standard is comma."""
        assert CSVSchema.DELIMITER == ','


class TestNormalizeHeader:
    """Tests for header normalization."""

    def test_normalize_canonical_header(self):
        """Test normalizing a canonical header name."""
        assert CSVSchema.normalize_header('project_name') == 'project_name'
        assert CSVSchema.normalize_header('project_task') == 'project_task'
        assert CSVSchema.normalize_header('monday') == 'monday'

    def test_normalize_legacy_header(self):
        """Test normalizing legacy header names."""
        assert CSVSchema.normalize_header('project_text') == 'project_name'
        assert CSVSchema.normalize_header('task') == 'project_task'

    def test_normalize_with_whitespace(self):
        """Test normalization strips whitespace."""
        assert CSVSchema.normalize_header('  project_name  ') == 'project_name'
        assert CSVSchema.normalize_header('  project_text  ') == 'project_name'

    def test_normalize_with_uppercase(self):
        """Test normalization converts to lowercase."""
        assert CSVSchema.normalize_header('PROJECT_NAME') == 'project_name'
        assert CSVSchema.normalize_header('Project_Name') == 'project_name'
        assert CSVSchema.normalize_header('PROJECT_TEXT') == 'project_name'

    def test_normalize_combined_transformations(self):
        """Test normalization with multiple transformations."""
        # Whitespace + uppercase + legacy alias
        assert CSVSchema.normalize_header('  PROJECT_TEXT  ') == 'project_name'
        assert CSVSchema.normalize_header('  TASK  ') == 'project_task'


class TestValidateHeaders:
    """Tests for header validation."""

    def test_validate_canonical_headers(self):
        """Test validation with canonical headers."""
        headers = [
            'project_number', 'project_name', 'project_task',
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]
        is_valid, error = CSVSchema.validate_headers(headers)
        assert is_valid is True
        assert error is None

    def test_validate_legacy_headers(self):
        """Test validation accepts legacy headers."""
        headers = [
            'project_number', 'project_text', 'task',  # Legacy names
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]
        is_valid, error = CSVSchema.validate_headers(headers)
        assert is_valid is True
        assert error is None

    def test_validate_mixed_headers(self):
        """Test validation with mix of canonical and legacy."""
        headers = [
            'project_number', 'project_text', 'project_task',  # Mixed
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]
        is_valid, error = CSVSchema.validate_headers(headers)
        assert is_valid is True
        assert error is None

    def test_validate_missing_headers(self):
        """Test validation fails with missing headers."""
        headers = ['project_number', 'monday', 'tuesday']
        is_valid, error = CSVSchema.validate_headers(headers)
        assert is_valid is False
        assert error is not None
        assert 'missing required headers' in error.lower()
        assert 'project_name' in error
        assert 'project_task' in error

    def test_validate_empty_headers(self):
        """Test validation fails with empty headers."""
        is_valid, error = CSVSchema.validate_headers([])
        assert is_valid is False
        assert error is not None
        assert 'empty' in error.lower()

    def test_validate_none_headers(self):
        """Test validation fails with None headers."""
        is_valid, error = CSVSchema.validate_headers(None)
        assert is_valid is False
        assert error is not None

    def test_validate_with_extra_headers(self):
        """Test validation succeeds with extra headers."""
        headers = [
            'project_number', 'project_name', 'project_task',
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday',
            'extra_column'  # Extra header should not cause failure
        ]
        is_valid, error = CSVSchema.validate_headers(headers)
        assert is_valid is True
        assert error is None

    def test_validate_case_insensitive(self):
        """Test validation is case-insensitive."""
        headers = [
            'PROJECT_NUMBER', 'Project_Name', 'project_TASK',
            'MONDAY', 'Tuesday', 'wednesday', 'THURSDAY',
            'friday', 'SATURDAY', 'sunday'
        ]
        is_valid, error = CSVSchema.validate_headers(headers)
        assert is_valid is True
        assert error is None


class TestCreateHeaderMapping:
    """Tests for header mapping creation."""

    def test_create_mapping_canonical(self):
        """Test creating mapping for canonical headers."""
        csv_headers = ['project_number', 'project_name', 'project_task']
        mapping = CSVSchema.create_header_mapping(csv_headers)

        assert mapping['project_number'] == 'project_number'
        assert mapping['project_name'] == 'project_name'
        assert mapping['project_task'] == 'project_task'

    def test_create_mapping_legacy(self):
        """Test creating mapping for legacy headers."""
        csv_headers = ['project_number', 'project_text', 'task']
        mapping = CSVSchema.create_header_mapping(csv_headers)

        assert mapping['project_number'] == 'project_number'
        assert mapping['project_text'] == 'project_name'  # Mapped
        assert mapping['task'] == 'project_task'  # Mapped

    def test_create_mapping_with_whitespace(self):
        """Test creating mapping handles whitespace."""
        csv_headers = ['  project_number  ', '  project_text  ', '  task  ']
        mapping = CSVSchema.create_header_mapping(csv_headers)

        # Keys should be normalized (stripped, lowercased)
        assert 'project_number' in mapping
        assert 'project_text' in mapping
        assert 'task' in mapping

        # Values should be canonical
        assert mapping['project_number'] == 'project_number'
        assert mapping['project_text'] == 'project_name'
        assert mapping['task'] == 'project_task'


class TestCSVSchemaIntegration:
    """Integration tests for CSV schema usage."""

    def test_schema_prevents_header_drift(self):
        """Test that schema guards against accidental header changes.

        This is a contract test - if this fails, it means someone changed
        the canonical headers, which would break backward compatibility.
        """
        # This test documents the expected header format
        expected_project_headers = ['project_number', 'project_name', 'project_task']
        expected_weekday_headers = [
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]

        actual_headers = CSVSchema.CANONICAL_HEADERS

        assert actual_headers[:3] == expected_project_headers, \
            "Project headers changed! This breaks backward compatibility."
        assert actual_headers[3:] == expected_weekday_headers, \
            "Weekday headers changed! This breaks backward compatibility."

    def test_legacy_to_canonical_mapping_complete(self):
        """Test that all legacy field names have canonical mappings."""
        legacy_fields = ['project_text', 'task']

        for legacy_field in legacy_fields:
            assert legacy_field in CSVSchema.LEGACY_ALIASES, \
                f"Legacy field '{legacy_field}' missing from LEGACY_ALIASES"

            canonical = CSVSchema.LEGACY_ALIASES[legacy_field]
            assert canonical in CSVSchema.CANONICAL_HEADERS, \
                f"Canonical mapping '{canonical}' not in CANONICAL_HEADERS"

    def test_round_trip_normalization(self):
        """Test that normalization is idempotent."""
        # Normalizing a canonical header should return itself
        for header in CSVSchema.CANONICAL_HEADERS:
            normalized = CSVSchema.normalize_header(header)
            assert normalized == header, \
                f"Canonical header '{header}' changed after normalization to '{normalized}'"

            # Normalizing again should still return the same value
            normalized_twice = CSVSchema.normalize_header(normalized)
            assert normalized_twice == normalized, \
                "Normalization is not idempotent"
