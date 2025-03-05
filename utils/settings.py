import logging
import logging.config
from pathlib import Path
from contextlib import suppress
from datetime import timedelta

import yaml


class InfoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == logging.INFO


class WarnFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARN


def setup_logging() -> None:
    log_config_path = Path(__file__).parent / "logging.yaml"
    with log_config_path.open() as f:
        log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)
    return None


def get_logger(logger_name: str | None = None) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    return logger


TOKEN = "MMM SWEET"
ALLOWED_CHAT_ID = {123}
PING_TIMEDELTA = timedelta(minutes=1)
DB_PATH = Path(__file__).parent.parent / "db.db"


WORDS: tuple[str] = ("блин",)

with suppress(ImportError):
    from utils.local_settings import *  # noqa F403
