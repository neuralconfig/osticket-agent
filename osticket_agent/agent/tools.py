"""Tools for the AI agent."""

import logging
from typing import Dict, List, Optional, Any

from smolagents import tool, Tool

from osticket_agent.api.osticket import Ticket, OSTicketClient
from osticket_agent.network.switch import (
    SwitchOperation,
    PortStatus,
    PoEStatus
)

# Set up logging
logger = logging.getLogger(__name__)


class GetTicketDetailsTool(Tool):
    name = "get_ticket_details"
    description = "Get details of a ticket"
    inputs = {
        "ticket_id": {
            "type": "integer",
            "description": "ID of the ticket"
        }
    }
    output_type = "object"

    def __init__(self, osticket_client: OSTicketClient):
        super().__init__()
        self.osticket_client = osticket_client

    def forward(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """
        Get details of a ticket.
        
        Args:
            ticket_id: ID of the ticket.
            
        Returns:
            Dictionary of ticket details or None if not found.
        """
        tickets = self.osticket_client.get_tickets()
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


class ReplyToTicketTool(Tool):
    name = "reply_to_ticket"
    description = "Reply to a ticket"
    inputs = {
        "ticket_id": {
            "type": "integer",
            "description": "ID of the ticket"
        },
        "message": {
            "type": "string",
            "description": "Message to send"
        }
    }
    output_type = "boolean"

    def __init__(self, osticket_client: OSTicketClient):
        super().__init__()
        self.osticket_client = osticket_client

    def forward(self, ticket_id: int, message: str) -> bool:
        """
        Reply to a ticket.
        
        Args:
            ticket_id: ID of the ticket.
            message: Message to send.
            
        Returns:
            True if successful, False otherwise.
        """
        return self.osticket_client.reply_to_ticket(ticket_id, message)


class CloseTicketTool(Tool):
    name = "close_ticket"
    description = "Close a ticket"
    inputs = {
        "ticket_id": {
            "type": "integer",
            "description": "ID of the ticket"
        },
        "message": {
            "type": "string",
            "description": "Closing message"
        }
    }
    output_type = "boolean"

    def __init__(self, osticket_client: OSTicketClient):
        super().__init__()
        self.osticket_client = osticket_client

    def forward(self, ticket_id: int, message: str) -> bool:
        """
        Close a ticket.
        
        Args:
            ticket_id: ID of the ticket.
            message: Closing message.
            
        Returns:
            True if successful, False otherwise.
        """
        return self.osticket_client.close_ticket(ticket_id, message)


class GetPortStatusTool(Tool):
    name = "get_port_status"
    description = "Get status of a port"
    inputs = {
        "switch_name": {
            "type": "string",
            "description": "Name of the switch"
        },
        "port": {
            "type": "string",
            "description": "Port name (e.g., '1/1/1')"
        }
    }
    output_type = "object"

    def __init__(self, switches: Dict[str, SwitchOperation]):
        super().__init__()
        self.switches = switches

    def forward(self, switch_name: str, port: str) -> Dict[str, Any]:
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
        if switch_name not in self.switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        switch = self.switches[switch_name]
        
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


class ChangePortVlanTool(Tool):
    name = "change_port_vlan"
    description = "Change VLAN of a port"
    inputs = {
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
    }
    output_type = "boolean"

    def __init__(self, switches: Dict[str, SwitchOperation]):
        super().__init__()
        self.switches = switches

    def forward(self, switch_name: str, port: str, vlan_id: int) -> bool:
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
        if switch_name not in self.switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        switch = self.switches[switch_name]
        
        with switch:
            success = switch.change_port_vlan(port, vlan_id)
            return success


class SetPortStatusTool(Tool):
    name = "set_port_status"
    description = "Set status of a port"
    inputs = {
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
            "description": "New status ('enable' or 'disable')"
        }
    }
    output_type = "boolean"

    def __init__(self, switches: Dict[str, SwitchOperation]):
        super().__init__()
        self.switches = switches

    def forward(self, switch_name: str, port: str, status: str) -> bool:
        """
        Set status of a port.
        
        Args:
            switch_name: Name of the switch.
            port: Port name.
            status: New status ("enable" or "disable").
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ValueError: If switch not found or status invalid.
        """
        if switch_name not in self.switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        try:
            port_status = PortStatus(status.lower())
        except ValueError:
            raise ValueError(f"Invalid port status '{status}'. Use 'enable' or 'disable'.")
        
        switch = self.switches[switch_name]
        
        with switch:
            success = switch.set_port_status(port, port_status)
            return success


class SetPoEStatusTool(Tool):
    name = "set_poe_status"
    description = "Set PoE status of a port"
    inputs = {
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
            "description": "New status ('enabled' or 'disabled')"
        }
    }
    output_type = "boolean"

    def __init__(self, switches: Dict[str, SwitchOperation]):
        super().__init__()
        self.switches = switches

    def forward(self, switch_name: str, port: str, status: str) -> bool:
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
        if switch_name not in self.switches:
            raise ValueError(f"Switch '{switch_name}' not found")
        
        try:
            poe_status = PoEStatus(status.lower())
        except ValueError:
            raise ValueError(
                f"Invalid PoE status '{status}'. Use 'enabled' or 'disabled'."
            )
        
        switch = self.switches[switch_name]
        
        with switch:
            success = switch.set_poe_status(port, poe_status)
            return success


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
    tools = [
        GetTicketDetailsTool(osticket_client),
        ReplyToTicketTool(osticket_client),
        CloseTicketTool(osticket_client),
        GetPortStatusTool(switches),
        ChangePortVlanTool(switches),
        SetPortStatusTool(switches),
        SetPoEStatusTool(switches)
    ]
    
    return tools