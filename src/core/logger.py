import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.core.config import settings

class PrefixFormatter(logging.Formatter):
    """
    Custom formatter with [i], [-], [+], [!] prefix based on log level.
    Uses a custom 'prefix' attribute instead of modifying record.msg.
    """
    LEVEL_PREFIX = {
        logging.DEBUG: "[i]",
        logging.INFO: "[+]",
        logging.WARNING: "[-]",
        logging.ERROR: "[!]",
        logging.CRITICAL: "[!]",
    }

    def format(self, record):
        # Add a 'prefix' attribute to the record
        record.prefix = self.LEVEL_PREFIX.get(record.levelno, "[ ]")
        return super().format(record)

def get_logger(name: str, log_file: Path = None) -> logging.Logger:
    if log_file is None:
        log_file = settings.logs_dir / f"{settings.app_name}.log"

    logger = logging.getLogger(name)
    if not logger.hasHandlers():  # Prevent adding handlers multiple times
        logger.setLevel(logging.DEBUG)

        # ------------------------
        # Console handler
        # ------------------------
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(
            PrefixFormatter(
                "%(asctime)s - %(name)s - %(prefix)s %(message)s",
                datefmt="%H:%M:%S"
            )
        )
        logger.addHandler(ch)

        # ------------------------
        # Rotating file handler
        # ------------------------
        fh = RotatingFileHandler(
            log_file,
            maxBytes=2_000_000,  # 2 MB per file
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
