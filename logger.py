# =========================================
# CENTRAL LOGGER (loguru)
# =========================================

from loguru import logger
import sys
from pathlib import Path
from config import config

# Create logs folder if it doesn't exist
Path(config.LOG_DIR).mkdir(exist_ok=True)

# Remove default handler
logger.remove()

# Console logging (beautiful & colored)
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# File logging (daily rotation)
logger.add(
    f"{config.LOG_DIR}/market_agent_{{time:YYYY-MM-DD}}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8"
)

# Export the logger
log = logger

log.info("Logger initialized successfully")