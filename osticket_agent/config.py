"""Configuration module for osTicket agent."""

import configparser
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class OSTicketConfig:
    """Configuration for osTicket API."""
    url: str
    api_key: str
    poll_interval: int = 60  # seconds


@dataclass
class NetworkDeviceConfig:
    """Configuration for a network device."""
    hostname: str
    username: str
    password: str
    device_type: str = "ruckus_fastiron"  # Netmiko device type for RUCKUS ICX


@dataclass
class Config:
    """Global configuration."""
    osticket: OSTicketConfig
    network_devices: Dict[str, NetworkDeviceConfig]
    openrouter_api_key: str
    model: str = "anthropic/claude-3-haiku"  # Default model


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from config.ini and environment variables.

    Args:
        config_path: Path to the config file. If None, defaults to config.ini
                     in the current directory.

    Returns:
        Config object with all configuration values.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        KeyError: If a required configuration value is missing.
    """
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Default to config.ini in the current directory if not specified
    if config_path is None:
        config_path = "config.ini"

    if not os.path.exists(config_path):
        template_path = Path(__file__).parent / "config.template.ini"
        raise FileNotFoundError(
            f"Config file {config_path} not found. "
            f"Create one based on the template at {template_path}"
        )

    parser = configparser.ConfigParser()
    parser.read(config_path)

    # Load osTicket configuration
    osticket_config = OSTicketConfig(
        url=parser["osticket"]["url"],
        api_key=parser["osticket"]["api_key"],
        poll_interval=int(parser["osticket"].get("poll_interval", "60")),
    )

    # Load network devices configuration
    network_devices = {}
    for section in parser.sections():
        if section.startswith("device:"):
            device_name = section[7:]  # Remove "device:" prefix
            network_devices[device_name] = NetworkDeviceConfig(
                hostname=parser[section]["hostname"],
                username=parser[section]["username"],
                password=parser[section]["password"],
                device_type=parser[section].get("device_type", "ruckus_fastiron"),
            )

    # Get OpenRouter API key from environment or config
    openrouter_api_key = os.environ.get(
        "OPENROUTER_API_KEY", 
        parser.get("openrouter", "api_key", fallback="")
    )

    if not openrouter_api_key:
        raise KeyError("OpenRouter API key not found. "
                       "Set it in config.ini or OPENROUTER_API_KEY environment variable.")

    # Get model name 
    model = parser.get("openrouter", "model", fallback="anthropic/claude-3-haiku")

    return Config(
        osticket=osticket_config,
        network_devices=network_devices,
        openrouter_api_key=openrouter_api_key,
        model=model,
    )