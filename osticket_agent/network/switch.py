"""Network operations for RUCKUS ICX switches."""

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import netmiko
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# Set up logging
logger = logging.getLogger(__name__)


class PortStatus(str, Enum):
    """Port status."""
    UP = "up"
    DOWN = "down"


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
            logger.info(f"Connected to {self.hostname}")
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
        return output
    
    def get_port_status(self, port: str) -> Optional[PortStatus]:
        """
        Get the status of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            
        Returns:
            Port status or None if port not found.
        """
        output = self.execute_command(f"show interfaces ethernet {port}")
        
        # Look for "port state: up" or "port state: down"
        match = re.search(r"port state: (up|down)", output, re.IGNORECASE)
        if match:
            status = match.group(1).lower()
            return PortStatus.UP if status == "up" else PortStatus.DOWN
        
        return None
    
    def get_port_vlan(self, port: str) -> Optional[int]:
        """
        Get the VLAN of a port.
        
        Args:
            port: Port name (e.g., "1/1/1").
            
        Returns:
            VLAN ID or None if port not found.
        """
        output = self.execute_command(f"show interfaces ethernet {port}")
        
        # Look for "Port {port} is a member of VLAN {vlan_id}"
        match = re.search(r"member of VLAN (\d+)", output, re.IGNORECASE)
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
        
        # Look for "State: On" or "State: Off"
        match = re.search(r"State: (On|Off)", output, re.IGNORECASE)
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
            commands = [
                f"vlan {vlan_id}",
                f"untagged ethernet {port}",
                "exit"
            ]
            
            self.configure(commands)
            
            # Verify the change
            new_vlan = self.get_port_vlan(port)
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
                "enable" if status == PortStatus.UP else "disable",
                "exit"
            ]
            
            self.configure(commands)
            
            # Verify the change
            new_status = self.get_port_status(port)
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
            
            # Verify the change
            new_status = self.get_poe_status(port)
            return new_status == status
        except Exception as e:
            logger.error(f"Failed to set PoE status on port {port}: {e}")
            return False