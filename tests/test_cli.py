from click.testing import CliRunner
from main import cli

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "report" in result.output
    assert "validate" in result.output
    assert "run" in result.output

def test_cli_config_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"])
    # May fail if MT5_PASSWORD/SERVER not set, but we set them in env for tests
    assert result.exit_code == 0
    assert "Current Configuration" in result.output
    assert "mt5_login" in result.output
