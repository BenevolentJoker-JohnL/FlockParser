"""
Logging configuration for FlockParser
Provides structured logging with different levels and handlers
Thread-safe configuration that works with Dask/distributed systems
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# CRITICAL: Disable Dask's distributed logging to prevent deadlocks in ThreadPoolExecutor
# Dask's logging handlers try to communicate with the distributed cluster which causes
# deadlocks when called from worker threads
import os

os.environ["DASK_DISTRIBUTED__LOGGING__DISTRIBUTED"] = "false"
os.environ["DASK_LOGGING__DISTRIBUTED"] = "false"

# Also disable bokeh logging from Dask dashboard
logging.getLogger("distributed").setLevel(logging.WARNING)
logging.getLogger("tornado").setLevel(logging.WARNING)
logging.getLogger("bokeh").setLevel(logging.WARNING)


def setup_logging(log_level: str = "INFO", log_file: bool = True, log_dir: Path = Path("logs")) -> logging.Logger:
    """
    Configure structured logging for FlockParser

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Whether to write logs to file
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("flockparser")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(fmt="%(levelname)s - %(message)s")

    # Console handler (user-friendly output)
    # Use sys.stderr instead of sys.stdout to avoid interfering with prompts
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed logging)
    if log_file:
        log_dir.mkdir(exist_ok=True)
        log_filename = log_dir / f"flockparser_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


# Create default logger instance
logger = setup_logging()


def get_logger(name: str = "flockparser") -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)
