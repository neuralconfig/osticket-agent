#!/usr/bin/env python3
"""Test script for network tools."""

import argparse
import logging
import sys
import time
from typing import Dict, List

from osticket_agent.config import load_config
from osticket_agent.network.switch import SwitchOperation, PortStatus, PoEStatus
from osticket_agent.agent.tools import (
    GetTicketDetailsTool,
    ReplyToTicketTool,
    CloseTicketTool,
    GetPortStatusTool,
    ChangePortVlanTool,
    SetPortStatusTool,
    SetPoEStatusTool,
    get_network_tools
)
from osticket_agent.api.osticket import OSTicketClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_get_port_status_tool(switch_name: str, port: str) -> None:
    """Test GetPortStatusTool."""
    logger.info(f"Testing GetPortStatusTool for switch {switch_name} port {port}")
    
    # Load configuration
    config = load_config()
    
    # Create SwitchOperation instances
    switches = {}
    for name, device_config in config.network_devices.items():
        switches[name] = SwitchOperation(
            hostname=device_config.hostname,
            username=device_config.username,
            password=device_config.password,
            device_type=device_config.device_type
        )
    
    # Create the tool
    tool = GetPortStatusTool(switches)
    
    # Run the tool
    try:
        result = tool.forward(switch_name, port)
        logger.info(f"Tool result: {result}")
    except Exception as e:
        logger.error(f"Tool error: {e}")

def test_change_port_vlan_tool(switch_name: str, port: str, vlan_id: int) -> None:
    """Test ChangePortVlanTool."""
    logger.info(f"Testing ChangePortVlanTool for switch {switch_name} port {port} vlan {vlan_id}")
    
    # Load configuration
    config = load_config()
    
    # Create SwitchOperation instances
    switches = {}
    for name, device_config in config.network_devices.items():
        switches[name] = SwitchOperation(
            hostname=device_config.hostname,
            username=device_config.username,
            password=device_config.password,
            device_type=device_config.device_type
        )
    
    # Create the tool
    tool = ChangePortVlanTool(switches)
    
    # Run the tool
    try:
        result = tool.forward(switch_name, port, vlan_id)
        logger.info(f"Tool result: {result}")
    except Exception as e:
        logger.error(f"Tool error: {e}")

def test_set_port_status_tool(switch_name: str, port: str, status: str) -> None:
    """Test SetPortStatusTool."""
    logger.info(f"Testing SetPortStatusTool for switch {switch_name} port {port} status {status}")
    
    # Load configuration
    config = load_config()
    
    # Create SwitchOperation instances
    switches = {}
    for name, device_config in config.network_devices.items():
        switches[name] = SwitchOperation(
            hostname=device_config.hostname,
            username=device_config.username,
            password=device_config.password,
            device_type=device_config.device_type
        )
    
    # Create the tool
    tool = SetPortStatusTool(switches)
    
    # Run the tool
    try:
        port_status = status.lower()
        if port_status not in ["enable", "disable"]:
            raise ValueError(f"Invalid port status '{status}'. Use 'enable' or 'disable'.")
            
        result = tool.forward(switch_name, port, port_status)
        logger.info(f"Tool result: {result}")
    except Exception as e:
        logger.error(f"Tool error: {e}")

def test_set_poe_status_tool(switch_name: str, port: str, status: str) -> None:
    """Test SetPoEStatusTool."""
    logger.info(f"Testing SetPoEStatusTool for switch {switch_name} port {port} status {status}")
    
    # Load configuration
    config = load_config()
    
    # Create SwitchOperation instances
    switches = {}
    for name, device_config in config.network_devices.items():
        switches[name] = SwitchOperation(
            hostname=device_config.hostname,
            username=device_config.username,
            password=device_config.password,
            device_type=device_config.device_type
        )
    
    # Create the tool
    tool = SetPoEStatusTool(switches)
    
    # Run the tool
    try:
        poe_status = status.lower()
        if poe_status not in ["enabled", "disabled"]:
            raise ValueError(f"Invalid PoE status '{status}'. Use 'enabled' or 'disabled'.")
            
        result = tool.forward(switch_name, port, poe_status)
        logger.info(f"Tool result: {result}")
    except Exception as e:
        logger.error(f"Tool error: {e}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test network tools")
    parser.add_argument("--tool", required=True, 
                      choices=["port-status", "change-vlan", "set-status", "set-poe"],
                      help="Tool to test")
    parser.add_argument("--switch", required=True, help="Switch name (from config)")
    parser.add_argument("--port", required=True, help="Port name (e.g., 1/1/1)")
    parser.add_argument("--value", help="Value for set operations (enable/disable, vlan ID, enabled/disabled)")
    
    args = parser.parse_args()
    
    # Run requested tool test
    if args.tool == "port-status":
        test_get_port_status_tool(args.switch, args.port)
    elif args.tool == "change-vlan":
        if not args.value:
            logger.error("--value (VLAN ID) required for change-vlan operation")
            sys.exit(1)
        test_change_port_vlan_tool(args.switch, args.port, int(args.value))
    elif args.tool == "set-status":
        if not args.value:
            logger.error("--value (enable/disable) required for set-status operation")
            sys.exit(1)
        test_set_port_status_tool(args.switch, args.port, args.value)
    elif args.tool == "set-poe":
        if not args.value:
            logger.error("--value (enabled/disabled) required for set-poe operation")
            sys.exit(1)
        test_set_poe_status_tool(args.switch, args.port, args.value)

if __name__ == "__main__":
    main()