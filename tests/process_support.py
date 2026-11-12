from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_EXPECTED_ERROR_USES_LOGURU_WITHOUT_TRACEBACK = "\nimport sys\nfrom fb_posts import app, main, LogLevelOption\nfrom fb_posts_lib.const import LogLevelName\nfrom fb_posts_lib.models import CollectionError\nfrom loguru import logger\n@app.command\ndef fail(*, log_level: LogLevelOption = LogLevelName.INFO):\n    log_level.reset_logger()\n    logger.debug('FIELD_DEBUG_DIAGNOSTIC')\n    raise CollectionError('Diagnóstico esperado')\nsys.argv = ['fb_posts.py', 'fail']\nmain()\n"
SCRIPT_UNEXPECTED_EXCEPTION_PRESERVES_STACK_WITHOUT_LEAKING_SECRETS = "\nimport sys\nfrom fb_posts import app, main\n@app.command\ndef fail():\n    token = 'PRIVATE_LOCAL_TOKEN'\n    try:\n        raise ValueError('PRIVATE_CHAINED_ERROR')\n    except ValueError as original:\n        raise OSError('PRIVATE_RAW_ERROR') from original\nsys.argv = ['fb_posts.py', 'fail']\nmain()\n"
SCRIPT_RICH_OUTPUT_PRESERVES_JSON_MARKUP_AND_LONG_STRINGS = (
    "\nfrom fb_posts import display_post\ndisplay_post({'message': '[bold]literal[/bold] ' + 'x' * 500})\n"
)

SCRIPT_COMMAND_LOG_LEVEL = (
    "import sys; from fb_posts import app; _, bound, _ = app.parse_args(sys.argv[1:]); bound.apply_defaults(); print(bound.arguments['log_level'].value)"
)
