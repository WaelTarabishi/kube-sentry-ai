import sys

from loguru import logger


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        colorize=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

