"""Logging utilities."""

import logging
import sys
from typing import Optional


def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_file: Path to log file. If None, logs only to stdout.
        verbose: If True, sets log level to DEBUG, otherwise INFO.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Set up basic configuration
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    # Set up third-party library logging to be less verbose
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("netmiko").setLevel(logging.INFO)