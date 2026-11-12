from collections.abc import Iterator

import pytest
from loguru import logger


@pytest.fixture
def messages() -> Iterator[list[str]]:
    records: list[str] = []
    handler = logger.add(lambda message: records.append(message.record["message"]), level="DEBUG", diagnose=False, backtrace=False)
    try:
        yield records
    finally:
        logger.remove(handler)
