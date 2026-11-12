import json
import os
import re
import subprocess
import sys

import pytest

from tests.process_support import (
    ROOT,
    SCRIPT_EXPECTED_ERROR_USES_LOGURU_WITHOUT_TRACEBACK,
    SCRIPT_RICH_OUTPUT_PRESERVES_JSON_MARKUP_AND_LONG_STRINGS,
    SCRIPT_UNEXPECTED_EXCEPTION_PRESERVES_STACK_WITHOUT_LEAKING_SECRETS,
)


@pytest.mark.integration
def test_expected_error_uses_loguru_without_traceback() -> None:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT_EXPECTED_ERROR_USES_LOGURU_WITHOUT_TRACEBACK],
        cwd=ROOT,
        env={key: value for key, value in os.environ.items() if key != "LOGURU_LEVEL"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.find("FIELD_DEBUG_DIAGNOSTIC") == -1
    output = re.sub("\\x1b\\[[0-9;]*m", "", result.stderr)
    assert output.count("Diagnóstico esperado") == 1
    assert output.find("Traceback") == -1


@pytest.mark.integration
def test_unexpected_exception_preserves_stack_without_leaking_secrets() -> None:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT_UNEXPECTED_EXCEPTION_PRESERVES_STACK_WITHOUT_LEAKING_SECRETS],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    assert bool(re.search("Traceback", result.stderr)) is True
    assert bool(re.search("in fail", result.stderr)) is True
    assert result.stderr.find("PRIVATE_LOCAL_TOKEN") == -1
    assert result.stderr.find("PRIVATE_CHAINED_ERROR") == -1
    assert result.stderr.find("PRIVATE_RAW_ERROR") == -1


@pytest.mark.integration
def test_rich_output_preserves_json_markup_and_long_strings() -> None:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT_RICH_OUTPUT_PRESERVES_JSON_MARKUP_AND_LONG_STRINGS],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"message": "[bold]literal[/bold] " + "x" * 500}
