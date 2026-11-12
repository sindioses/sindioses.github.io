import os
import subprocess
import sys

import pytest

from tests.process_support import ROOT, SCRIPT_COMMAND_LOG_LEVEL


@pytest.mark.parametrize("command", [["collect", "2026-01-01"], ["gen"], ["sample", "--post-id", "123_1"], ["credential", "set"], ["credential", "check"]])
@pytest.mark.parametrize(
    "environment_level,options,expected",
    [(None, [], "INFO"), ("WARNING", [], "WARNING"), ("WARNING", ["-L", "DEBUG"], "DEBUG"), ("WARNING", ["--log-level", "ERROR"], "ERROR")],
)
@pytest.mark.integration
def test_commands_share_configured_logging_precedence(command: list[str], environment_level: str | None, options: list[str], expected: str) -> None:
    environment = {key: value for key, value in os.environ.items() if key != "LOGURU_LEVEL"}
    if environment_level is not None:
        environment["LOGURU_LEVEL"] = environment_level
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT_COMMAND_LOG_LEVEL, *command, *options],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    "environment_level,options,diagnostics", [(None, [], 1), ("CRITICAL", [], 0), ("CRITICAL", ["-L", "ERROR"], 1), ("ERROR", ["-L", "CRITICAL"], 0)]
)
@pytest.mark.integration
def test_collect_applies_resolved_level_before_validation(environment_level: str | None, options: list[str], diagnostics: int) -> None:
    environment = {key: value for key, value in os.environ.items() if key != "LOGURU_LEVEL"}
    if environment_level is not None:
        environment["LOGURU_LEVEL"] = environment_level
    result = subprocess.run(
        [sys.executable, str(ROOT / "fb_posts.py"), "collect", "2026-01-01", "--page-id", "invalid", *options],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr.count("El ID de página debe ser numérico.") == diagnostics
    assert result.stderr.find("Traceback") == -1
