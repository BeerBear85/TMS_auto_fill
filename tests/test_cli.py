"""
Tests for CLI argument parsing and validation.

This module tests the command-line interface, including argument parsing,
validation, and the --weeks argument functionality.
"""

import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock
from argparse import Namespace

from timesheet_bot.cli import create_parser, validate_args, cmd_fill
from timesheet_bot.config import Config
from timesheet_bot.week_utils import WeekRangeParseError


class TestCreateParser:
    """Tests for create_parser function."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == 'timesheet_bot'

    def test_parser_has_fill_command(self):
        """Test that parser has 'fill' subcommand."""
        parser = create_parser()
        # Parse a minimal valid command
        args = parser.parse_args(['fill', '--csv', 'test.csv'])
        assert args.command == 'fill'
        assert args.csv == 'test.csv'

    def test_csv_argument_required(self):
        """Test that --csv argument is required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['fill'])

    def test_weeks_argument_optional(self):
        """Test that --weeks argument is optional."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv'])
        assert args.weeks is None

    def test_weeks_argument_accepts_value(self):
        """Test that --weeks argument accepts a value."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '--weeks', '48-50'])
        assert args.weeks == '48-50'

    def test_headless_flag(self):
        """Test that --headless flag works."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '--headless'])
        assert args.headless is True

    def test_auto_submit_flag(self):
        """Test that --auto-submit flag works."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '--auto-submit'])
        assert args.auto_submit is True

    def test_dry_run_flag(self):
        """Test that --dry-run flag works."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '--dry-run'])
        assert args.dry_run is True

    def test_no_overwrite_flag(self):
        """Test that --no-overwrite flag works."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '--no-overwrite'])
        assert args.no_overwrite is True

    def test_verbose_flag(self):
        """Test that --verbose flag works."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '--verbose'])
        assert args.verbose is True

    def test_verbose_short_flag(self):
        """Test that -v flag works for verbose."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', 'test.csv', '-v'])
        assert args.verbose is True

    def test_multiple_flags_combined(self):
        """Test that multiple flags can be used together."""
        parser = create_parser()
        args = parser.parse_args([
            'fill',
            '--csv', 'test.csv',
            '--weeks', '48-50',
            '--headless',
            '--no-overwrite',
            '--verbose'
        ])
        assert args.csv == 'test.csv'
        assert args.weeks == '48-50'
        assert args.headless is True
        assert args.no_overwrite is True
        assert args.verbose is True


class TestValidateArgs:
    """Tests for validate_args function."""

    @pytest.fixture
    def temp_csv(self, tmp_path):
        """Create a temporary CSV file for testing."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("project_number,monday\n8-12345-10-01,7.5\n")
        return str(csv_file)

    def test_validate_valid_args(self, temp_csv):
        """Test validation with valid arguments."""
        args = Namespace(
            csv=temp_csv,
            weeks=None,
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        assert validate_args(args) is True

    def test_validate_csv_not_found(self):
        """Test validation fails when CSV file doesn't exist."""
        args = Namespace(
            csv='nonexistent.csv',
            weeks=None,
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        assert validate_args(args) is False

    def test_validate_dry_run_and_auto_submit_conflict(self, temp_csv):
        """Test validation fails with conflicting --dry-run and --auto-submit."""
        args = Namespace(
            csv=temp_csv,
            weeks=None,
            dry_run=True,
            auto_submit=True,
            verbose=False
        )
        assert validate_args(args) is False

    def test_validate_weeks_single(self, temp_csv):
        """Test validation with single week number."""
        args = Namespace(
            csv=temp_csv,
            weeks='48',
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is True
        assert hasattr(args, 'parsed_weeks')
        assert args.parsed_weeks == [48]

    def test_validate_weeks_range(self, temp_csv):
        """Test validation with week range."""
        args = Namespace(
            csv=temp_csv,
            weeks='48-50',
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is True
        assert hasattr(args, 'parsed_weeks')
        assert args.parsed_weeks == [48, 49, 50]

    def test_validate_weeks_comma_separated(self, temp_csv):
        """Test validation with comma-separated weeks."""
        args = Namespace(
            csv=temp_csv,
            weeks='48,49,50',
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is True
        assert hasattr(args, 'parsed_weeks')
        assert args.parsed_weeks == [48, 49, 50]

    def test_validate_weeks_combined(self, temp_csv):
        """Test validation with combined format."""
        args = Namespace(
            csv=temp_csv,
            weeks='48-50,52',
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is True
        assert hasattr(args, 'parsed_weeks')
        assert args.parsed_weeks == [48, 49, 50, 52]

    def test_validate_weeks_invalid_format(self, temp_csv):
        """Test validation fails with invalid week format."""
        args = Namespace(
            csv=temp_csv,
            weeks='48-',  # Invalid: incomplete range
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is False

    def test_validate_weeks_out_of_range(self, temp_csv):
        """Test validation fails with week out of range."""
        args = Namespace(
            csv=temp_csv,
            weeks='54',  # Invalid: week > 53
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is False

    def test_validate_weeks_zero(self, temp_csv):
        """Test validation fails with week 0."""
        args = Namespace(
            csv=temp_csv,
            weeks='0',  # Invalid: week < 1
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is False

    def test_validate_weeks_invalid_characters(self, temp_csv):
        """Test validation fails with invalid characters."""
        args = Namespace(
            csv=temp_csv,
            weeks='abc',  # Invalid: not numbers
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is False

    def test_validate_weeks_empty_string(self, temp_csv):
        """Test validation fails with empty string."""
        args = Namespace(
            csv=temp_csv,
            weeks='',  # Invalid: empty
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is False

    def test_validate_weeks_none(self, temp_csv):
        """Test validation succeeds with weeks=None."""
        args = Namespace(
            csv=temp_csv,
            weeks=None,
            dry_run=False,
            auto_submit=False,
            verbose=False
        )
        result = validate_args(args)
        assert result is True
        assert hasattr(args, 'parsed_weeks')
        assert args.parsed_weeks is None


class TestWeeksArgumentIntegration:
    """Integration tests for --weeks argument end-to-end."""

    @pytest.fixture
    def temp_csv(self, tmp_path):
        """Create a temporary CSV file for testing."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "project_number,project_name,project_task,monday,tuesday\n"
            "8-12345-10-01,Test Project,Task 1,7.5,7.5\n"
        )
        return str(csv_file)

    def test_config_created_with_weeks(self, temp_csv):
        """Test that Config object is created correctly with weeks parameter."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', temp_csv, '--weeks', '48-50'])

        # Validate args (which adds parsed_weeks)
        validate_args(args)

        # Create config
        config = Config(
            csv_path=args.csv,
            weeks=args.parsed_weeks,
            headless=args.headless,
            auto_submit=args.auto_submit,
            no_overwrite=args.no_overwrite,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        assert config.weeks == [48, 49, 50]
        assert config.csv_path == temp_csv

    def test_config_validation_with_weeks(self, temp_csv):
        """Test that Config validation works with weeks parameter."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', temp_csv, '--weeks', '48-50'])

        validate_args(args)

        config = Config(
            csv_path=args.csv,
            weeks=args.parsed_weeks,
            headless=False,
            auto_submit=False,
            no_overwrite=False,
            dry_run=False,
            verbose=False
        )

        # Should not raise
        config.validate()

    def test_parser_to_config_single_week(self, temp_csv):
        """Test full flow from parser to config with single week."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', temp_csv, '--weeks', '48'])

        validate_args(args)

        config = Config(
            csv_path=args.csv,
            weeks=args.parsed_weeks,
            headless=False,
            auto_submit=False,
            no_overwrite=False,
            dry_run=False,
            verbose=False
        )

        config.validate()
        assert config.weeks == [48]

    def test_parser_to_config_no_weeks(self, temp_csv):
        """Test full flow from parser to config without --weeks."""
        parser = create_parser()
        args = parser.parse_args(['fill', '--csv', temp_csv])

        validate_args(args)

        config = Config(
            csv_path=args.csv,
            weeks=args.parsed_weeks,
            headless=False,
            auto_submit=False,
            no_overwrite=False,
            dry_run=False,
            verbose=False
        )

        config.validate()
        assert config.weeks is None

    def test_weeks_with_auto_submit(self, temp_csv):
        """Test --weeks combined with --auto-submit."""
        parser = create_parser()
        args = parser.parse_args([
            'fill',
            '--csv', temp_csv,
            '--weeks', '48-50',
            '--auto-submit'
        ])

        validate_args(args)

        config = Config(
            csv_path=args.csv,
            weeks=args.parsed_weeks,
            headless=False,
            auto_submit=True,
            no_overwrite=False,
            dry_run=False,
            verbose=False
        )

        config.validate()
        assert config.weeks == [48, 49, 50]
        assert config.auto_submit is True

    def test_weeks_with_no_overwrite(self, temp_csv):
        """Test --weeks combined with --no-overwrite."""
        parser = create_parser()
        args = parser.parse_args([
            'fill',
            '--csv', temp_csv,
            '--weeks', '48-50',
            '--no-overwrite'
        ])

        validate_args(args)

        config = Config(
            csv_path=args.csv,
            weeks=args.parsed_weeks,
            headless=False,
            auto_submit=False,
            no_overwrite=True,
            dry_run=False,
            verbose=False
        )

        config.validate()
        assert config.weeks == [48, 49, 50]
        assert config.no_overwrite is True
