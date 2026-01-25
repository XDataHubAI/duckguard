"""Tests for the CLI."""

from typer.testing import CliRunner

from duckguard.cli.main import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "DuckGuard" in result.stdout

    def test_info_command(self, orders_csv):
        """Test info command."""
        result = runner.invoke(app, ["info", orders_csv])
        assert result.exit_code == 0
        assert "Rows" in result.stdout
        assert "Columns" in result.stdout

    def test_discover_command(self, orders_csv):
        """Test discover command."""
        result = runner.invoke(app, ["discover", orders_csv])
        assert result.exit_code == 0
        assert "Discovering" in result.stdout

    def test_discover_with_yaml_output(self, orders_csv, tmp_path):
        """Test discover command generates YAML output."""
        result = runner.invoke(app, ["discover", orders_csv])
        assert result.exit_code == 0
        # Should show generated rules panel
        assert "Generated Rules" in result.stdout or "rules" in result.stdout.lower()

    def test_check_command(self, orders_csv):
        """Test check command."""
        result = runner.invoke(app, ["check", orders_csv, "--unique", "order_id"])
        assert result.exit_code == 0
        assert "PASS" in result.stdout

    def test_check_command_failure(self, orders_csv):
        """Test check command with failing check."""
        result = runner.invoke(app, ["check", orders_csv, "--unique", "customer_id"])
        assert result.exit_code == 1
        assert "FAIL" in result.stdout

    def test_discover_nonexistent_file(self):
        """Test discover with non-existent file."""
        result = runner.invoke(app, ["discover", "nonexistent.csv"])
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_info_nonexistent_file(self):
        """Test info with non-existent file."""
        result = runner.invoke(app, ["info", "nonexistent.csv"])
        assert result.exit_code == 1
