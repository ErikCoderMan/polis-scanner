import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.core.config import settings
from src.ui.log_buffer import log_buffer


class PrefixFormatter(logging.Formatter):
    LEVEL_PREFIX = {
        logging.DEBUG: "[i]",
        logging.INFO: "[+]",
        logging.WARNING: "[-]",
        logging.ERROR: "[!]",
        logging.CRITICAL: "[!]",
    }

    def format(self, record):
        record.prefix = self.LEVEL_PREFIX.get(record.levelno, "[ ]")
        return super().format(record)


class UILogHandler(logging.Handler):
    """Send logs to prompt_toolkit UI instead of stdout"""

    def emit(self, record):
        msg = self.format(record)
        log_buffer.write(msg)


def get_logger(name: str, log_file: Path = None) -> logging.Logger:
    if log_file is None:
        log_file = settings.logs_dir / f"{settings.app_name}.log"

    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # UI handler (replaces console)
    ui = UILogHandler()
    ui.setLevel(logging.INFO)
    ui.setFormatter(
        PrefixFormatter(
            "%(asctime)s - %(name)s - %(prefix)s %(message)s",
            datefmt="%H:%M:%S"
        )
    )
    logger.addHandler(ui)

    # file handler
    fh = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        PrefixFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    logger.addHandler(fh)

    return logger
