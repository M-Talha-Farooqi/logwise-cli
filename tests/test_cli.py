from typer.testing import CliRunner

from logwise.cli import app

runner = CliRunner()


def test_file_not_found_exits_2():
    result = runner.invoke(app, ["analyze", "/no/such/file.log"])
    assert result.exit_code == 2


def test_analyze_stdin():
    # feed a clean line via stdin
    result = runner.invoke(app, ["analyze", "-"], input="2024-03-15T14:23:01Z 10.0.0.7 GET /a 200 5ms\n")
    assert result.exit_code in (0, 1)       # 0 normally; 1 only if 5xx/high-malformed
