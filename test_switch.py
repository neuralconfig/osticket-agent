#!/usr/bin/env python3
"""Test script for switch tools."""

import argparse
import logging
import sys
import time
from typing import Dict

from osticket_agent.config import load_config
from osticket_agent.network.switch import SwitchOperation, PortStatus, PoEStatus

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_get_port_status(switch: SwitchOperation, port: str) -> None:
    """Test get_port_status."""
    logger.info(f"Testing get_port_status for port {port}")
    status = switch.get_port_status(port)
    logger.info(f"Port status: {status}")

def test_get_port_vlan(switch: SwitchOperation, port: str) -> None:
    """Test get_port_vlan."""
    logger.info(f"Testing get_port_vlan for port {port}")
    vlan = switch.get_port_vlan(port)
    logger.info(f"Port VLAN: {vlan}")

def test_get_poe_status(switch: SwitchOperation, port: str) -> None:
    """Test get_poe_status."""
    logger.info(f"Testing get_poe_status for port {port}")
    status = switch.get_poe_status(port)
    logger.info(f"PoE status: {status}")

def test_set_port_status(switch: SwitchOperation, port: str, status: str) -> None:
    """Test set_port_status."""
    logger.info(f"Testing set_port_status for port {port} to {status}")
    port_status = PortStatus.ENABLE if status.lower() == "enable" else PortStatus.DISABLE
    success = switch.set_port_status(port, port_status)
    logger.info(f"Set port status success: {success}")
    
    # Wait for change to apply
    logger.info("Waiting 3 seconds for change to apply...")
    time.sleep(3)
    
    # Verify
    current_status = switch.get_port_status(port)
    logger.info(f"Current port status: {current_status}")

def test_change_port_vlan(switch: SwitchOperation, port: str, vlan_id: int) -> None:
    """Test change_port_vlan."""
    logger.info(f"Testing change_port_vlan for port {port} to VLAN {vlan_id}")
    success = switch.change_port_vlan(port, vlan_id)
    logger.info(f"Change port VLAN success: {success}")
    
    # Wait for change to apply
    logger.info("Waiting 3 seconds for change to apply...")
    time.sleep(3)
    
    # Verify
    current_vlan = switch.get_port_vlan(port)
    logger.info(f"Current port VLAN: {current_vlan}")

def test_set_poe_status(switch: SwitchOperation, port: str, status: str) -> None:
    """Test set_poe_status."""
    logger.info(f"Testing set_poe_status for port {port} to {status}")
    poe_status = PoEStatus.ENABLED if status.lower() == "enabled" else PoEStatus.DISABLED
    success = switch.set_poe_status(port, poe_status)
    logger.info(f"Set PoE status success: {success}")
    
    # Wait for change to apply
    logger.info("Waiting 3 seconds for change to apply...")
    time.sleep(3)
    
    # Verify
    current_status = switch.get_poe_status(port)
    logger.info(f"Current PoE status: {current_status}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test switch operations")
    parser.add_argument("--switch", required=True, help="Switch name (from config)")
    parser.add_argument("--port", required=True, help="Port name (e.g., 1/1/1)")
    parser.add_argument("--operation", required=True, 
                        choices=["status", "vlan", "poe", "set-status", "set-vlan", "set-poe", "all"],
                        help="Operation to test")
    parser.add_argument("--value", help="Value for set operations (enable/disable, vlan ID, enabled/disabled)")
    
    args = parser.parse_args()
    
    # Load configuration
    logger.info("Loading configuration...")
    config = load_config()
    
    if args.switch not in config.network_devices:
        logger.error(f"Switch {args.switch} not found in configuration")
        sys.exit(1)
    
    # Get switch configuration
    switch_config = config.network_devices[args.switch]
    logger.info(f"Using switch {args.switch} with hostname {switch_config.hostname}")
    
    # Create switch operation object
    switch = SwitchOperation(
        hostname=switch_config.hostname,
        username=switch_config.username,
        password=switch_config.password,
        device_type=switch_config.device_type
    )
    
    # Connect to switch
    try:
        switch.connect()
        
        # Run requested operation
        if args.operation == "status" or args.operation == "all":
            test_get_port_status(switch, args.port)
        
        if args.operation == "vlan" or args.operation == "all":
            test_get_port_vlan(switch, args.port)
        
        if args.operation == "poe" or args.operation == "all":
            test_get_poe_status(switch, args.port)
        
        if args.operation == "set-status":
            if not args.value:
                logger.error("Value (enable/disable) required for set-status operation")
                sys.exit(1)
            test_set_port_status(switch, args.port, args.value)
        
        if args.operation == "set-vlan":
            if not args.value:
                logger.error("Value (VLAN ID) required for set-vlan operation")
                sys.exit(1)
            test_change_port_vlan(switch, args.port, int(args.value))
        
        if args.operation == "set-poe":
            if not args.value:
                logger.error("Value (enabled/disabled) required for set-poe operation")
                sys.exit(1)
            test_set_poe_status(switch, args.port, args.value)
        
    finally:
        # Disconnect from switch
        switch.disconnect()

if __name__ == "__main__":
    main()