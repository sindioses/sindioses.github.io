import json
import os
import re
import subprocess
import sys
import unittest

from fb_posts_lib.storage import ROOT


class LoggingTests(unittest.TestCase):
    def test_log_level_uses_environment_with_info_fallback(self):
        for level, visible in ((None, {"INFO", "WARNING"}), ("DEBUG", {"DEBUG", "INFO", "WARNING"}), ("WARNING", {"WARNING"})):
            with self.subTest(level=level):
                environment = {key: value for key, value in os.environ.items() if key != "LOGURU_LEVEL"}
                if level is not None:
                    environment["LOGURU_LEVEL"] = level
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from fb_posts import logger; logger.debug('DEBUG_MARKER'); logger.info('INFO_MARKER'); logger.warning('WARNING_MARKER')",
                    ],
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                for severity in ("DEBUG", "INFO", "WARNING"):
                    self.assertEqual(f"{severity}_MARKER" in result.stderr, severity in visible)

    def test_expected_error_uses_loguru_without_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
from fb_posts import app, main
from fb_posts_lib.models import CollectionError
from loguru import logger
@app.command
def fail():
    logger.debug('FIELD_DEBUG_DIAGNOSTIC')
    raise CollectionError('Diagnóstico esperado')
sys.argv = ['fb_posts.py', 'fail']
main()
""",
            ],
            cwd=ROOT,
            env={key: value for key, value in os.environ.items() if key != "LOGURU_LEVEL"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("FIELD_DEBUG_DIAGNOSTIC", result.stderr)
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.stderr)
        self.assertRegex(output, r"\d{4}-\d{2}-\d{2} .* \| ERROR\s+\| fb_posts:main:\d+ - Diagnóstico esperado\n")

    def test_unexpected_exception_preserves_stack_without_leaking_secrets(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
from fb_posts import app, main
@app.command
def fail():
    token = 'PRIVATE_LOCAL_TOKEN'
    try:
        raise ValueError('PRIVATE_CHAINED_ERROR')
    except ValueError as original:
        raise OSError('PRIVATE_RAW_ERROR') from original
sys.argv = ['fb_posts.py', 'fail']
main()
""",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual("Traceback" in result.stderr, True)
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.stderr)
        self.assertEqual(" | ERROR " in output, True)
        self.assertEqual("Error interno de tipo OSError" in result.stderr, True)
        self.assertEqual("PRIVATE_LOCAL_TOKEN" in result.stderr, False)
        self.assertEqual("PRIVATE_CHAINED_ERROR" in result.stderr, False)
        self.assertEqual("PRIVATE_RAW_ERROR" in result.stderr, False)

    def test_rich_output_preserves_json_markup_and_long_strings(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
from fb_posts import display_post
display_post({'message': '[bold]literal[/bold] ' + 'x' * 500})
""",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {"message": "[bold]literal[/bold] " + "x" * 500})
