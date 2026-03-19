import sys
import os
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    """Configure application-wide logging using loguru."""
    log_level = settings.log_level.upper()
    log_file = settings.log_file

    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler — human-readable in dev, JSON-like in prod
    if settings.app_env == "development":
        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=log_level,
            format="{time:YYYY-MM-DDTHH:mm:ss.SSS}Z | {level} | {name}:{function}:{line} | {message}",
            serialize=False,
        )

    # Rotating file handler
    logger.add(
        log_file,
        level=log_level,
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DDTHH:mm:ss.SSS}Z | {level} | {name}:{function}:{line} | {message}",
        enqueue=True,   # async-safe
    )

    logger.info(f"Logging initialised | level={log_level} | env={settings.app_env}")


# Expose a pre-configured logger for import anywhere in the app
__all__ = ["logger", "setup_logging"]
