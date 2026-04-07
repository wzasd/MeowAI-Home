from click.testing import CliRunner
from src.cli.main import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'meowai' in result.output


def test_cli_chat_command_exists():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'chat' in result.output
