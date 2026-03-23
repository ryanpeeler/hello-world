"""Tests for CLI argument parsing."""

from researchclaw.cli import main


def test_cli_no_args(capsys):
    """CLI with no args should print help and return 0."""
    result = main([])
    assert result == 0
    captured = capsys.readouterr()
    assert "researchclaw" in captured.out.lower() or "usage" in captured.out.lower()


def test_cli_help(capsys):
    """CLI --help should work (via SystemExit)."""
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0
