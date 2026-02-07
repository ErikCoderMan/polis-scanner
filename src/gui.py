from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

def run_gui():
    logger.info(f"Data dir: {settings.data_dir}")
    print("GUI is running...")
