from pathlib import Path
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# -------------------------------------------------------------
# Environment loader
# -------------------------------------------------------------
def _load_dotenv():
    """
    Try loading .env from project root (parent.parent),
    otherwise fallback to home config location.
    """

    repo_env = Path(__file__).resolve().parent.parent.parent / ".env"
    home_env = Path.home() / ".polis-scanner" / ".env"

    # Priority 1: repo root
    if repo_env.exists():
        load_dotenv(repo_env)
        return repo_env

    # Priority 2: home config
    if home_env.exists():
        load_dotenv(home_env)
        return home_env

    # If nothing exists, create .env in project root (preferred)
    repo_env.parent.mkdir(parents=True, exist_ok=True)
    repo_env.touch(exist_ok=True)

    load_dotenv(repo_env)

    return repo_env


# -------------------------------------------------------------
# Settings dataclass
# -------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    env_path: Path

    app_name: str
    version: str

    base_dir: Path
    data_dir: Path
    logs_dir: Path
    cache_dir: Path

    polis_base_url: str
    polis_event_url: str

    poll_interval: str
    poll_interval_lowest_allowed_s: int
    poll_interval_lowest_recomended_s: int

    http_timeout_s: int
    http_backoff_s: int
    http_backoff_max_s: int
    http_backoff_modifier: float
    http_max_retries: int

    shutdown_grace_period: int
    command_history_len: int
    
    default_theme: str


# -------------------------------------------------------------
# Global singleton
# -------------------------------------------------------------
settings: Settings = None


# -------------------------------------------------------------
# Settings loader
# -------------------------------------------------------------
def load_settings(force_reload: bool = False) -> Settings:
    global settings

    if settings is not None and not force_reload:
        return settings

    env_path = _load_dotenv()

    base_dir = Path(
        os.environ.get("POLIS_SCANNER_BASE_DIR")
        or Path(__file__).resolve().parent.parent.parent
    )

    data_dir = Path(
        os.environ.get("POLIS_SCANNER_DATA_DIR")
        or (base_dir / "data")
    )

    logs_dir = Path(
        os.environ.get("POLIS_SCANNER_LOGS_DIR")
        or (data_dir / "logs")
    )

    cache_dir = Path(
        os.environ.get("POLIS_SCANNER_CACHE_DIR")
        or (data_dir / "cache")
    )

    settings = Settings(
        env_path=env_path,
        app_name=os.environ.get("POLIS_SCANNER_NAME") or "polis-scanner",
        version=os.environ.get("POLIS_SCANNER_VERSION") or "0.0.1",
        base_dir=base_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
        polis_base_url=os.environ.get(
            "POLIS_SCANNER_POLIS_BASE_URL",
            "https://polisen.se"
        ),
        polis_event_url=os.environ.get(
            "POLIS_SCANNER_POLIS_EVENT_URL",
            "https://polisen.se/api/events"
        ),
        poll_interval=os.environ.get(
            "POLIS_SCANNER_POLL_INTERVAL",
            "5m"
        ),
        poll_interval_lowest_allowed_s=int(
            os.environ.get(
                "POLIS_SCANNER_POLL_INTERVALL_LOWEST_ALLOWED_S",
                10
            )
        ),
        poll_interval_lowest_recomended_s=int(
            os.environ.get(
                "POLIS_SCANNER_POLL_INTERVAL_LOWEST_RECOMENDED_S",
                60
            )
        ),
        http_timeout_s=int(
            os.environ.get("POLIS_SCANNER_HTTP_TIMEOUT_S", 10)
        ),
        http_backoff_s=int(
            os.environ.get("POLIS_SCANNER_HTTP_BACKOFF_S", 4)
        ),
        http_backoff_max_s=int(
            os.environ.get("POLIS_SCANNER_HTTP_BACKOFF_MAX_S", 12)
        ),
        http_backoff_modifier=float(
            os.environ.get(
                "POLIS_SCANNER_HTTP_BACKOFF_MODIFIER",
                1.5
            )
        ),
        http_max_retries=int(
            os.environ.get("POLIS_SCANNER_HTTP_RETRIES", 3)
        ),
        shutdown_grace_period=int(
            os.environ.get(
                "POLIS_SCANNER_SHUTDOWN_GRACE_PERIOD",
                10
            )
        ),
        command_history_len=int(
            os.environ.get(
                "POLIS_SCANNER_COMMAND_HISTORY_LEN",
                1000
            )
        ),
        default_theme=(
            os.environ.get(
                "POLIS_SCANNER_DEFAULT_THEME",
                "default"
            )
        )
    )

    return settings


# -------------------------------------------------------------
# Environment variable updater
# -------------------------------------------------------------
def update_env_variable(key: str, value: str) -> None:
    global settings

    if settings is None:
        settings = load_settings()

    env_path = settings.env_path

    if not env_path.exists():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines = []

    found = False

    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines), encoding="utf-8")

    # reload runtime settings after update
    load_settings(force_reload=True)


# -------------------------------------------------------------
# Initialize singleton immediately (important!)
# -------------------------------------------------------------
settings = load_settings()
