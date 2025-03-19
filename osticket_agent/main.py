"""Main entry point for the osTicket agent."""

import argparse
import logging
import sys
from typing import Dict, List, Optional

from osticket_agent.config import load_config, Config
from osticket_agent.api.osticket import OSTicketClient
from osticket_agent.network.switch import SwitchOperation
from osticket_agent.agent.agent import NetworkAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("osticket_agent.log")
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="osTicket Network Agent")
    parser.add_argument(
        "--config", "-c",
        help="Path to config file (default: config.ini)",
        default="config.ini"
    )
    parser.add_argument(
        "--verbose", "-v",
        help="Enable verbose logging",
        action="store_true"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = load_config(args.config)
        
        # Set up osTicket client
        osticket_client = OSTicketClient(
            url=config.osticket.url,
            api_key=config.osticket.api_key
        )
        
        # Set up switch connections
        switches = {}
        for name, device_config in config.network_devices.items():
            switches[name] = SwitchOperation(
                hostname=device_config.hostname,
                username=device_config.username,
                password=device_config.password,
                device_type=device_config.device_type
            )
        
        # Create and run the agent
        agent = NetworkAgent(
            osticket_client=osticket_client,
            openrouter_api_key=config.openrouter_api_key,
            switches=switches,
            model=config.model
        )
        
        logger.info("Starting agent")
        agent.run(poll_interval=config.osticket.poll_interval)
    
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyError as e:
        logger.error(f"Missing configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()