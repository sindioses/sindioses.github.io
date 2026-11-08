import os
import sys

from loguru import logger
from enum import StrEnum, auto
from pathlib import Path


class LogLevelName(StrEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.upper()

    TRACE = auto()
    DEBUG = auto()
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

    def reset_logger(self):
        logger.remove()
        logger.add(sys.stderr, level=os.getenv("LOGURU_LEVEL", self.value))


IMAGE_ROOT = Path(__file__).parents[1] / "images"

POST_ROOT = Path(__file__).parents[1] / "posts"
POST_TEMPLATE = """\
.. author: {author}
.. title: {title}
.. date: {date}
.. category: {category}
.. type: {type}
.. link: {link}
.. description: {description}


.. class:: primera

{body}

"""

SQL_POST_QUERY = """\
SELECT
    *,
    json_extract(raw_json, '$.attachments.data[0].media.image.src') AS image
FROM posts
WHERE
    message IS NOT NULL
    AND category || slug || author IS NOT NULL
    AND length(message) > 2000
    AND (:cut_date is NULL or created_time > :cut_date)
ORDER BY created_time;
"""

THUMBNAIL_TEMPLATE = """\
..  thumbnail:: {0}
    :class: align-right
"""
