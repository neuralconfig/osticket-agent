"""Network operations for RUCKUS ICX switches."""

import logging
import re
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import netmiko
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# Set up logging
logger = logging.getLogger(__name__)


class PortStatus(str, Enum):
    """Port status."""
    ENABLE = "enable"
    DISABLE = "disable"


class PoEStatus(str, Enum):
    """PoE status."""
    ENABLED = "enabled"
    DISABLED = "disabled"


class SwitchOperation:
    """Network switch operations."""
    
    def __init__(
        self, 
        hostname: str, 
        username: str, 
        password: str, 
        device_type: str = "ruckus_fastiron"
    ):
        """
        Initialize switch operations.
        
        Args:
            hostname: Switch hostname or IP address.
            username: SSH username.
            password: SSH password.
            device_type: Netmiko device type.
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.device_type = device_type
        self._connection = None
    
    def connect(self) -> None:
        """
        Connect to the switch.
        
        Raises:
            NetmikoTimeoutException: If connection times out.
            NetmikoAuthenticationException: If authentication fails.
        """
        if self._connection is not None and self._connection.is_alive():
            return
        
        device = {
            "device_type": self.device_type,
            "host": self.hostname,
            "username": self.username,
            "password": self.password,
        }
        
        try:
            logger.info(f"Connecting to {self.hostname}...")
            self._connection = ConnectHandler(**device)
            # Enter enable mode
            self._connection.enable()
            logger.info(f"Connected to {self.hostname} and entered enable mode")
        except NetmikoTimeoutException:
            logger.error(f"Connection to {self.hostname} timed out")
            raise
        except NetmikoAuthenticationException:
            logger.error(f"Authentication to {self.hostname} failed")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from the switch."""
        if self._connection is not None and self._connection.is_alive():
            self._connection.disconnect()
            logger.info(f"Disconnected from {self.hostname}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def execute_command(self, command: str) -> str:
        """
        Execute a command on the switch.
        
        Args:
            command: Command to execute.
            
        Returns:
            Command output.
            
        Raises:
            ConnectionError: If not connected to the switch.
        """
        if self._connection is None or not self._connection.is_alive():
            raise ConnectionError("Not connected to switch")
        
        logger.debug(f"Executing command: {command}")
        output = self._connection.send_command(command)
        logger.debug(f"Command output: {output}")
        return output
    
    def configure(self, commands: List[str]) -> str:
        """
        Configure the switch with a list of commands.
        
        Args:
            commands: List of configuration commands.
            
        Returns:
            Configuration output.
            
        Raises:
            ConnectionError: If not connected to the switch.
        """
        if self._connection is None or not self._connection.is_alive():
            raise ConnectionError("Not connected to switch")
        
        logger.debug(f"Configuring with commands: {commands}")
        output = self._connection.send_config_set(commands)
        logger.debug(f"Configuration output: {output}")
        return output
    
    def get_port_status(self, port: str) -> Optional[PortStatus]:
        """
        Get the status of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            
        Returns:
            Port status or None if port not found.
        """
        # Use show int br command to get status
        output = self.execute_command(f"show int br e {port}")
        
        # Check for status from brief output
        # Format: Port Link State Dupl Speed Trunk Tag Pvid Pri MAC Name
        # Sample: 1/1/1 Up Forward Full 1G None No 1 0 94b3.4f31.485c 
        # Sample: 1/1/1 Disable None None None None No 1 0 94b3.4f31.485c 
        # Sample: 1/1/1 Down None None None None No 1 0 94b3.4f31.485c
        
        # Extract the Link column which will be Up, Down, or Disable
        port_pattern = re.escape(port)
        match = re.search(rf"{port_pattern}\s+(\w+)", output)
        
        if match:
            status = match.group(1).lower()
            # "Disable" means port is administratively down
            # "Up" or "Down" means port is administratively up (enabled)
            return PortStatus.DISABLE if status == "disable" else PortStatus.ENABLE
        
        return None
    
    def get_port_vlan(self, port: str) -> Optional[int]:
        """
        Get the VLAN of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            
        Returns:
            VLAN ID or None if port not found.
        """
        # Use show vlan brief command to get VLAN
        output = self.execute_command(f"show vlan br e {port}")
        
        # Look for "Untagged VLAN : X"
        match = re.search(r"Untagged VLAN\s+:\s+(\d+)", output, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Alternatively, look for "VLANs X" in case of different output format
        match = re.search(r"VLANs\s+(\d+)", output, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None
    
    def get_poe_status(self, port: str) -> Optional[PoEStatus]:
        """
        Get the PoE status of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            
        Returns:
            PoE status or None if port doesn't support PoE.
        """
        output = self.execute_command(f"show inline power {port}")
        
        if "Invalid input" in output or "No information available" in output:
            return None
        
        # Look for "Admin State On/Off" in the output table
        # Format: Port Admin Oper ---Power(mWatts)--- PD Type PD Class Pri Fault/
        #         State State Consumed Allocated                       Error
        # Sample: 1/1/1 On Off 0 0 n/a n/a 3 n/a
        
        port_pattern = re.escape(port)
        match = re.search(rf"\s+{port_pattern}\s+(On|Off)", output)
        
        if match:
            state = match.group(1).lower()
            return PoEStatus.ENABLED if state == "on" else PoEStatus.DISABLED
        
        return None
    
    def change_port_vlan(self, port: str, vlan_id: int) -> bool:
        """
        Change the VLAN of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            vlan_id: New VLAN ID.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # First get current VLAN
            current_vlan = self.get_port_vlan(port)
            logger.info(f"Current VLAN for port {port}: {current_vlan}")
            
            # Commands to move port from current VLAN to new VLAN
            commands = []
            
            # Try to remove from current VLAN first (may fail for default VLAN)
            if current_vlan:
                commands.extend([
                    f"vlan {current_vlan}",
                    f"no untagged ethernet {port}",
                    "exit"
                ])
            
            # Add to new VLAN
            commands.extend([
                f"vlan {vlan_id}",
                f"untagged ethernet {port}",
                "exit"
            ])
            
            # Execute commands
            self.configure(commands)
            
            # Save configuration with write memory command
            self.execute_command("write memory")
            logger.info("Configuration saved with 'write memory'")
            
            # Wait for change to apply
            logger.info("Waiting for VLAN change to apply...")
            time.sleep(3)
            
            # Verify the change
            new_vlan = self.get_port_vlan(port)
            logger.info(f"New VLAN for port {port}: {new_vlan}")
            return new_vlan == vlan_id
        except Exception as e:
            logger.error(f"Failed to change VLAN on port {port}: {e}")
            return False
    
    def set_port_status(self, port: str, status: PortStatus) -> bool:
        """
        Set the status of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            status: New port status.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            commands = [
                f"interface ethernet {port}",
                "enable" if status == PortStatus.ENABLE else "disable",
                "exit"
            ]
            
            self.configure(commands)
            
            # Save configuration with write memory command
            self.execute_command("write memory")
            logger.info("Configuration saved with 'write memory'")
            
            # Wait for change to apply
            logger.info("Waiting for port status change to apply...")
            time.sleep(3)
            
            # Verify the change
            new_status = self.get_port_status(port)
            logger.info(f"New status for port {port}: {new_status}")
            
            # Verify status matches expected status
            return new_status == status
        except Exception as e:
            logger.error(f"Failed to set status on port {port}: {e}")
            return False
    
    def set_poe_status(self, port: str, status: PoEStatus) -> bool:
        """
        Set the PoE status of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            status: New PoE status.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            commands = [
                f"interface ethernet {port}",
                "inline power" if status == PoEStatus.ENABLED else "no inline power",
                "exit"
            ]
            
            self.configure(commands)
            
            # Wait for change to apply
            logger.info("Waiting for PoE status change to apply...")
            time.sleep(3)
            
            # Verify the change - note that PoE changes can take longer
            new_status = self.get_poe_status(port)
            logger.info(f"New PoE status for port {port}: {new_status}")
            
            return new_status == status
        except Exception as e:
            logger.error(f"Failed to set PoE status on port {port}: {e}")
            return False