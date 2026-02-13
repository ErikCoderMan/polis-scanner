from pathlib import Path
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# -------------------------------------------------------------
# Load environment variables from .env
# -------------------------------------------------------------
def _load_dotenv():
    # 1. Try .env in current working directory (dev/project root)
    dev_env = Path.cwd() / ".env"
    if dev_env.exists():
        load_dotenv(dev_env)
    # 2. Fallback to installed version in home folder
    else:
        home_env = Path.home() / ".polis-scanner" / ".env"
        if home_env.exists():
            load_dotenv(home_env)

# -------------------------------------------------------------
# Settings dataclass
# -------------------------------------------------------------
@dataclass
class Settings:
    app_name: str
    version: str
    base_dir: Path
    data_dir: Path
    logs_dir: Path
    cache_dir: Path
    polis_event_url: str
    poll_interval_s: int
    http_timeout_s: int

    def __post_init__(self):
        # Ensure directories exist
        for directory in [self.data_dir, self.logs_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# Global instance (initialized by load_settings)
# -------------------------------------------------------------
settings: Settings = None

def load_settings() -> Settings:
    global settings
    if settings is not None:
        return settings  # already loaded

    _load_dotenv()

    base_dir = Path(os.environ.get("POLIS_SCANNER_BASE_DIR") or Path(__file__).resolve().parent.parent.parent)
    data_dir = Path(os.environ.get("POLIS_SCANNER_DATA_DIR") or (base_dir / "data"))
    logs_dir = Path(os.environ.get("POLIS_SCANNER_LOGS_DIR") or (data_dir / "logs"))
    cache_dir = Path(os.environ.get("POLIS_SCANNER_CACHE_DIR") or (data_dir / "cache"))

    settings = Settings(
        app_name=os.environ.get("POLIS_SCANNER_NAME") or "polis-scanner",
        version=os.environ.get("POLIS_SCANNER_VERSION") or "0.0.1",
        base_dir=base_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
        polis_event_url=os.environ.get("POLIS_SCANNER_POLIS_EVENT_URL", "https://polisen.se/api/events"),
        poll_interval_s = os.environ.get("POLIS_SCANNER_POLL_INTERVALL_S", 60),
        http_timeout_s = os.environ.get("POLIS_SCANNER_HTTP_TIMEOUT_S", 10)
    )
    return settings

# Initialize global instance immediately
settings = load_settings()
