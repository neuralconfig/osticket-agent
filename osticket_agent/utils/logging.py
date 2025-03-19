"""Logging utilities."""

import logging
import sys
from typing import Optional


def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_file: Path to log file. If None, logs only to stdout.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Set up basic configuration
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        # Use a more detailed format for file logging
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Use a simpler format for console output
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handlers[0].setFormatter(console_formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers
    )
    
    # Set up module-specific log levels
    logging.getLogger("osticket_agent").setLevel(level)
    
    # Always keep third-party libraries less verbose unless in DEBUG mode
    if level <= logging.DEBUG:
        logging.getLogger("urllib3").setLevel(logging.INFO)
        logging.getLogger("netmiko").setLevel(logging.INFO)
    else:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("netmiko").setLevel(logging.WARNING)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level: {logging.getLevelName(level)}")
    if log_file:
        logger.info(f"Log file: {log_file}")