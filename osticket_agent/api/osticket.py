"""osTicket API client."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests
from pydantic import BaseModel, Field

# Set up logging
logger = logging.getLogger(__name__)


class TicketStatus:
    """Constants for ticket status IDs."""
    ALL = 0
    OPEN = 1
    RESOLVED = 2
    CLOSED = 3
    ARCHIVED = 4
    DELETED = 5
    ONGOING = 6
    PENDING = 7


class Ticket(BaseModel):
    """Model for an osTicket ticket."""
    id: int
    number: str
    subject: str
    description: str
    status_id: int = Field(alias="status")
    status_name: str
    created: datetime
    updated: datetime
    department_id: int = Field(alias="dept_id")
    department_name: str = Field(alias="dept")
    priority_id: int
    priority_name: str = Field(alias="priority")
    
    # Flag to track if this ticket has been processed by our agent
    processed: bool = False
    
    @property
    def is_open(self) -> bool:
        """Check if the ticket is open."""
        return self.status_id == TicketStatus.OPEN
    
    class Config:
        """Pydantic model configuration."""
        populate_by_name = True


class OSTicketClient:
    """Client for the osTicket API."""
    
    def __init__(self, url: str, api_key: str):
        """
        Initialize the osTicket API client.
        
        Args:
            url: Base URL for the osTicket API.
            api_key: API key for authentication.
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }
    
    def get_tickets(
        self, 
        status_id: int = TicketStatus.OPEN,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Ticket]:
        """
        Get tickets from osTicket.
        
        Args:
            status_id: Status ID to filter tickets by.
            start_date: Start date for ticket range (YYYY-MM-DD HH:MM:SS).
            end_date: End date for ticket range (YYYY-MM-DD HH:MM:SS).
            
        Returns:
            List of Ticket objects.
            
        Raises:
            requests.RequestException: If the API request fails.
        """
        if not start_date:
            # Default to 30 days ago
            start_date = (datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        if not end_date:
            # Default to now
            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        payload = {
            "query": "ticket",
            "condition": "all",
            "sort": "creationDate",
            "parameters": {
                "start_date": start_date,
                "end_date": end_date,
            }
        }
        
        if status_id != TicketStatus.ALL:
            payload["parameters"]["status_id"] = status_id
        
        response = requests.get(
            self.url, 
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] != "Success":
            error_msg = f"API Error: {data.get('data', 'Unknown error')}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        tickets_data = data.get("data", [])
        tickets = []
        
        for ticket_data in tickets_data:
            try:
                ticket = Ticket.model_validate(ticket_data)
                tickets.append(ticket)
            except Exception as e:
                logger.warning(f"Failed to parse ticket: {e}")
        
        return tickets
    
    def reply_to_ticket(self, ticket_id: int, message: str, staff_id: int = 1) -> bool:
        """
        Reply to a ticket.
        
        Args:
            ticket_id: ID of the ticket to reply to.
            message: HTML formatted message to send.
            staff_id: ID of the staff member making the reply.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            requests.RequestException: If the API request fails.
        """
        payload = {
            "query": "ticket",
            "condition": "reply",
            "parameters": {
                "ticket_id": ticket_id,
                "body": f"<p>{message}</p>",
                "staff_id": staff_id
            }
        }
        
        response = requests.post(
            self.url, 
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] != "Success":
            error_msg = f"API Error: {data.get('data', 'Unknown error')}"
            logger.error(error_msg)
            return False
        
        return True
    
    def close_ticket(
        self, 
        ticket_id: int, 
        message: str, 
        staff_id: int = 1,
        staff_name: str = "Network Agent"
    ) -> bool:
        """
        Close a ticket.
        
        Args:
            ticket_id: ID of the ticket to close.
            message: HTML formatted closing message.
            staff_id: ID of the staff member closing the ticket.
            staff_name: Name of the staff member closing the ticket.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            requests.RequestException: If the API request fails.
        """
        payload = {
            "query": "ticket",
            "condition": "close",
            "parameters": {
                "ticket_id": ticket_id,
                "body": f"<p>{message}</p>",
                "staff_id": staff_id,
                "status_id": TicketStatus.CLOSED,
                "team_id": 1,
                "dept_id": 1,
                "topic_id": 1,
                "username": staff_name
            }
        }
        
        response = requests.post(
            self.url, 
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        
        data = response.json()
        if data["status"] != "Success":
            error_msg = f"API Error: {data.get('data', 'Unknown error')}"
            logger.error(error_msg)
            return False
        
        return True