"""Tools for the AI agent."""

import logging
from typing import Dict, List, Optional, Any

from smolagents.runner.tool import Tool

from osticket_agent.api.osticket import Ticket, OSTicketClient
from osticket_agent.network.switch import (
    SwitchOperation,
    PortStatus,
    PoEStatus
)

# Set up logging
logger = logging.getLogger(__name__)


def get_network_tools(
    osticket_client: OSTicketClient,
    switches: Dict[str, SwitchOperation]
) -> List[Tool]:
    """
    Get tools for network operations.
    
    Args:
        osticket_client: OSTicketClient instance.
        switches: Dictionary of switch name to SwitchOperation instance.
        
    Returns:
        List of network tools.
    """
    tools = []
    
    def get_ticket_details(ticket_id: int) -> Optional[Dict[str, Any]]:
        """
        Get details of a ticket.
        
        Args:
            ticket_id: ID of the ticket.
            
        Returns:
            Dictionary of ticket details or None if not found.
        """
        tickets = osticket_client.get_tickets()
        for ticket in tickets:
            if ticket.id == ticket_id:
                return {
                    "id": ticket.id,
                    "number": ticket.number,
                    "subject": ticket.subject,
                    "description": ticket.description,
                    "status": ticket.status_name,
                    "created": ticket.created.isoformat(),
                    "department": ticket.department_name,
                    "priority": ticket.priority_name,
                }
        return None
    
    def reply_to_ticket(ticket_id: int, message: str) -> bool:
        """
        Reply to a ticket.
        
        Args:
            ticket_id: ID of the ticket.
            message: Message to send.
            
        Returns:
            True if successful, False otherwise.
        """
        return osticket_client.reply_to_ticket(ticket_id, message)
    
    def close_ticket(ticket_id: int, message: str) -> bool:
        """
        Close a ticket.
        
        Args:
            ticket_id: ID of the ticket.
            message: Closing message.
            
        Returns:
            True if successful, False otherwise.
        """
        return osticket_client.close_ticket(ticket_id, message)
    
    def get_switch_list() -> List[str]:
        """
        Get list of available switches.
        
        Returns:
            List of switch names.
        """
        return list(switches.keys())
    
    def get_port_status(switch_name: str, port: str) -> Dict[str, Any]:
        """
        Get status of a port.
        
        Args:
            switch_name: Name of the switch.
            port: Port name.
            
        Returns:
            Dictionary of port status information.
            
        Raises:
            ValueError: If switch not found.
        """
        if switch_name not in switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        switch = switches[switch_name]
        
        with switch:
            port_status = switch.get_port_status(port)
            vlan = switch.get_port_vlan(port)
            poe_status = switch.get_poe_status(port)
            
            return {
                "port": port,
                "status": port_status.value if port_status else "unknown",
                "vlan": vlan,
                "poe_status": poe_status.value if poe_status else "not supported",
            }
    
    def change_port_vlan(switch_name: str, port: str, vlan_id: int) -> bool:
        """
        Change VLAN of a port.
        
        Args:
            switch_name: Name of the switch.
            port: Port name.
            vlan_id: New VLAN ID.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ValueError: If switch not found.
        """
        if switch_name not in switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        switch = switches[switch_name]
        
        with switch:
            success = switch.change_port_vlan(port, vlan_id)
            return success
    
    def set_port_status(switch_name: str, port: str, status: str) -> bool:
        """
        Set status of a port.
        
        Args:
            switch_name: Name of the switch.
            port: Port name.
            status: New status ("up" or "down").
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ValueError: If switch not found or status invalid.
        """
        if switch_name not in switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        try:
            port_status = PortStatus(status.lower())
        except ValueError:
            raise ValueError(f"Invalid port status '{status}'. Use 'up' or 'down'.")
        
        switch = switches[switch_name]
        
        with switch:
            success = switch.set_port_status(port, port_status)
            return success
    
    def set_poe_status(switch_name: str, port: str, status: str) -> bool:
        """
        Set PoE status of a port.
        
        Args:
            switch_name: Name of the switch.
            port: Port name.
            status: New status ("enabled" or "disabled").
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ValueError: If switch not found or status invalid.
        """
        if switch_name not in switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        try:
            poe_status = PoEStatus(status.lower())
        except ValueError:
            raise ValueError(
                f"Invalid PoE status '{status}'. Use 'enabled' or 'disabled'."
            )
        
        switch = switches[switch_name]
        
        with switch:
            success = switch.set_poe_status(port, poe_status)
            return success
    
    # Define tools
    tools.extend([
        Tool(
            name="get_ticket_details",
            description="Get details of a ticket",
            function=get_ticket_details,
            parameters={
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket"
                }
            },
            returns={
                "type": "object",
                "description": "Ticket details or null if not found"
            }
        ),
        Tool(
            name="reply_to_ticket",
            description="Reply to a ticket",
            function=reply_to_ticket,
            parameters={
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket"
                },
                "message": {
                    "type": "string",
                    "description": "Message to send"
                }
            },
            returns={
                "type": "boolean",
                "description": "True if successful, False otherwise"
            }
        ),
        Tool(
            name="close_ticket",
            description="Close a ticket",
            function=close_ticket,
            parameters={
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket"
                },
                "message": {
                    "type": "string",
                    "description": "Closing message"
                }
            },
            returns={
                "type": "boolean",
                "description": "True if successful, False otherwise"
            }
        ),
        Tool(
            name="get_switch_list",
            description="Get list of available switches",
            function=get_switch_list,
            parameters={},
            returns={
                "type": "array",
                "description": "List of switch names",
                "items": {
                    "type": "string"
                }
            }
        ),
        Tool(
            name="get_port_status",
            description="Get status of a port",
            function=get_port_status,
            parameters={
                "switch_name": {
                    "type": "string",
                    "description": "Name of the switch"
                },
                "port": {
                    "type": "string",
                    "description": "Port name (e.g., '1/1/1')"
                }
            },
            returns={
                "type": "object",
                "description": "Port status information"
            }
        ),
        Tool(
            name="change_port_vlan",
            description="Change VLAN of a port",
            function=change_port_vlan,
            parameters={
                "switch_name": {
                    "type": "string",
                    "description": "Name of the switch"
                },
                "port": {
                    "type": "string",
                    "description": "Port name (e.g., '1/1/1')"
                },
                "vlan_id": {
                    "type": "integer",
                    "description": "New VLAN ID"
                }
            },
            returns={
                "type": "boolean",
                "description": "True if successful, False otherwise"
            }
        ),
        Tool(
            name="set_port_status",
            description="Set status of a port",
            function=set_port_status,
            parameters={
                "switch_name": {
                    "type": "string",
                    "description": "Name of the switch"
                },
                "port": {
                    "type": "string",
                    "description": "Port name (e.g., '1/1/1')"
                },
                "status": {
                    "type": "string",
                    "description": "New status ('up' or 'down')",
                    "enum": ["up", "down"]
                }
            },
            returns={
                "type": "boolean",
                "description": "True if successful, False otherwise"
            }
        ),
        Tool(
            name="set_poe_status",
            description="Set PoE status of a port",
            function=set_poe_status,
            parameters={
                "switch_name": {
                    "type": "string",
                    "description": "Name of the switch"
                },
                "port": {
                    "type": "string",
                    "description": "Port name (e.g., '1/1/1')"
                },
                "status": {
                    "type": "string",
                    "description": "New status ('enabled' or 'disabled')",
                    "enum": ["enabled", "disabled"]
                }
            },
            returns={
                "type": "boolean",
                "description": "True if successful, False otherwise"
            }
        )
    ])
    
    return tools