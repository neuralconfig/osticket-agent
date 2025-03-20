"""osTicket API client."""

import json
import logging
from datetime import datetime, timedelta
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
        # Add debugging to see what status is being checked
        logger.debug(f"Checking if ticket {self.id} is open: status_id={self.status_id}, TicketStatus.OPEN={TicketStatus.OPEN}")
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
            ) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        if not end_date:
            # Default to 7 days in the future to account for any time zone differences
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            
        logger.debug(f"Using date range: {start_date} to {end_date}")
        
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
        
        # Create a custom request to exactly mimic the curl command with --data-binary
        # Using a GET request with a JSON body as specified in the reference
        import urllib3
        http = urllib3.PoolManager()
        
        encoded_data = json.dumps(payload).encode('utf-8')
        
        response = http.request(
            'GET',
            self.url,
            body=encoded_data,
            headers=self.headers
        )
        
        # Convert the urllib3 response to a format compatible with our existing code
        response_text = response.data.decode('utf-8')
        logger.debug(f"Raw API response: {response_text}")
        
        data = json.loads(response_text)
        logger.debug(f"Parsed API response structure: {json.dumps(data, indent=2)}")
        
        # Check response status
        if data.get("status") != "Success":
            error_msg = f"API Error: {data.get('data', 'Unknown error')}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # The API returns a complex nested structure
        data_content = data.get("data", {})
        
        logger.debug(f"Received data structure: {type(data_content).__name__}")
        if isinstance(data_content, dict):
            logger.debug(f"Data content keys: {list(data_content.keys())}")
        
        # Extract tickets from various possible response structures
        tickets = []
        
        # Try different extraction methods based on the observed response format
        if isinstance(data_content, dict):
            # Case 1: If we have a 'ticket' key with a list of tickets
            if "ticket" in data_content and isinstance(data_content["ticket"], list):
                logger.debug(f"Found 'ticket' list with {len(data_content['ticket'])} items")
                for ticket_item in data_content["ticket"]:
                    try:
                        if not isinstance(ticket_item, dict):
                            logger.debug(f"Ticket item is not a dict: {type(ticket_item)}")
                            continue
                            
                        # Map the API response fields to our Ticket model fields
                        ticket_data = {
                            "id": int(ticket_item.get("ticket_id", 0)),
                            "number": ticket_item.get("number", ""),
                            "subject": ticket_item.get("subject", ""),
                            "description": ticket_item.get("message", ""),
                            "status": int(ticket_item.get("status_id", 0)),
                            "status_name": ticket_item.get("status", ""),
                            "created": ticket_item.get("created", ""),
                            "updated": ticket_item.get("updated", ""),
                            "dept_id": int(ticket_item.get("dept_id", 0)),
                            "dept": ticket_item.get("dept_name", ""),
                            "priority_id": int(ticket_item.get("priority_id", 0)),
                            "priority": ticket_item.get("priority", "")
                        }
                        
                        ticket = Ticket.model_validate(ticket_data)
                        tickets.append(ticket)
                        logger.debug(f"Successfully parsed ticket ID: {ticket.id}")
                    except Exception as e:
                        logger.debug(f"Failed to parse ticket item: {e}")
            
            # Case 2: If we have 'tickets' key with a list of ticket history arrays
            elif "tickets" in data_content and isinstance(data_content["tickets"], list):
                logger.debug(f"Found 'tickets' list with {len(data_content['tickets'])} items")
                
                for ticket_history in data_content["tickets"]:
                    try:
                        # Each item is a list of ticket history entries
                        if isinstance(ticket_history, list) and len(ticket_history) > 0:
                            # Get the most recent entry (last in the array)
                            most_recent = ticket_history[-1]
                            logger.debug(f"Processing ticket ID: {most_recent.get('ticket_id')}, Status: {most_recent.get('status_id')}")
                            
                            # Convert API datetime strings to Python datetime objects
                            created_date = datetime.strptime(most_recent.get("created", ""), "%Y-%m-%d %H:%M:%S") if most_recent.get("created") else datetime.now()
                            updated_date = datetime.strptime(most_recent.get("updated", ""), "%Y-%m-%d %H:%M:%S") if most_recent.get("updated") else datetime.now()
                            
                            # Map the API fields to our Ticket model
                            ticket_data = {
                                "id": int(most_recent.get("ticket_id", 0)),
                                "number": most_recent.get("number", ""),
                                "subject": most_recent.get("subject", ""),
                                "description": most_recent.get("body", ""),
                                "status": int(most_recent.get("status_id", 0)),
                                "status_name": "Open" if most_recent.get("status_id") == "1" else 
                                              "Resolved" if most_recent.get("status_id") == "2" else
                                              "Closed" if most_recent.get("status_id") == "3" else
                                              "Unknown",
                                "created": created_date,
                                "updated": updated_date,
                                "dept_id": int(most_recent.get("dept_id", 0)),
                                "dept": "Support",  # Default value as it's not in the API response
                                "priority_id": int(most_recent.get("priority_id", 1)) if most_recent.get("priority_id") else 1,
                                "priority": "Normal"  # Default value
                            }
                            
                            # Create the ticket object
                            ticket = Ticket.model_validate(ticket_data)
                            
                            # Print details about all tickets for debugging
                            logger.debug(f"Ticket details - ID: {most_recent.get('ticket_id')}, Number: {most_recent.get('number')}, "
                                         f"Subject: '{most_recent.get('subject')}', Status ID: {most_recent.get('status_id')}, "
                                         f"Created: {most_recent.get('created')}")
                                         
                            # Only include if it's an open ticket (status_id = 1)
                            # Temporarily include all tickets for debugging
                            tickets.append(ticket)
                            logger.debug(f"Added ticket ID: {ticket.id} with status: {most_recent.get('status_id')}")
                        else:
                            logger.debug(f"Ticket history is not a list or is empty")
                    except Exception as e:
                        logger.debug(f"Failed to parse ticket from 'tickets' list: {e}")
                        
        # Case 3: If the data is a direct list of tickets
        elif isinstance(data_content, list):
            logger.debug(f"Data is a direct list with {len(data_content)} items")
            for ticket_data in data_content:
                try:
                    ticket = Ticket.model_validate(ticket_data)
                    tickets.append(ticket)
                except Exception as e:
                    logger.debug(f"Failed to parse ticket from direct list: {e}")
                    
        logger.debug(f"Successfully extracted {len(tickets)} tickets")
        
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
        
        # Create a custom request to exactly mimic the curl command with --data-binary
        import urllib3
        http = urllib3.PoolManager()
        
        encoded_data = json.dumps(payload).encode('utf-8')
        
        response = http.request(
            'POST',
            self.url,
            body=encoded_data,
            headers=self.headers
        )
        
        # Convert the urllib3 response to a format compatible with our existing code
        data = json.loads(response.data.decode('utf-8'))
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
        
        # Create a custom request to exactly mimic the curl command with --data-binary
        import urllib3
        http = urllib3.PoolManager()
        
        encoded_data = json.dumps(payload).encode('utf-8')
        
        response = http.request(
            'POST',
            self.url,
            body=encoded_data,
            headers=self.headers
        )
        
        # Convert the urllib3 response to a format compatible with our existing code
        data = json.loads(response.data.decode('utf-8'))
        if data["status"] != "Success":
            error_msg = f"API Error: {data.get('data', 'Unknown error')}"
            logger.error(error_msg)
            return False
        
        return True