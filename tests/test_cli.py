import json
import pytest
from cli import run


def test_cli_effect_size(capsys):
    assert run(["--effect-size", "0.5", "--alpha", "0.05", "--power", "0.8"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["sample_size"] == 34
    assert result["df"] == 33


def test_cli_difference_mode(capsys):
    assert run(["--mean-diff", "5", "--sd-diff", "10"]) == 0
    assert json.loads(capsys.readouterr().out)["sample_size"] == 34


def test_cli_group_mode(capsys):
    assert run(["--mean1", "140", "--mean2", "135", "--sd1", "10", "--sd2", "10", "--correlation", "0.5"]) == 0
    assert json.loads(capsys.readouterr().out)["sample_size"] == 34


def test_cli_invalid_effect_size(capsys):
    assert run(["--effect-size", "-0.5"]) == 2
    assert "Effect size" in capsys.readouterr().err


def test_cli_missing_mode():
    with pytest.raises(SystemExit) as err:
        run([])
    assert err.value.code == 2


def test_cli_incomplete_mode():
    with pytest.raises(SystemExit) as err:
        run(["--mean-diff", "5"])
    assert err.value.code == 2
