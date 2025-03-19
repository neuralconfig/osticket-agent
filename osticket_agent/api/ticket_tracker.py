"""Ticket tracker to manage processed tickets."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Set

from osticket_agent.api.osticket import Ticket

# Set up logging
logger = logging.getLogger(__name__)


class TicketTracker:
    """Track which tickets have been processed by the agent."""
    
    def __init__(self, storage_path: str = "ticket_tracker.json"):
        """
        Initialize the ticket tracker.
        
        Args:
            storage_path: Path to the JSON file to store processed ticket IDs.
        """
        self.storage_path = storage_path
        self.processed_tickets: Set[int] = set()
        self.load()
    
    def load(self) -> None:
        """Load processed ticket IDs from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.processed_tickets = set(data.get("processed_tickets", []))
                logger.info(f"Loaded {len(self.processed_tickets)} processed tickets")
            except Exception as e:
                logger.error(f"Failed to load ticket tracker: {e}")
                # Initialize with empty set if load fails
                self.processed_tickets = set()
    
    def save(self) -> None:
        """Save processed ticket IDs to storage."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump({
                    "processed_tickets": list(self.processed_tickets),
                    "last_updated": datetime.now().isoformat()
                }, f)
            logger.debug(f"Saved {len(self.processed_tickets)} processed tickets")
        except Exception as e:
            logger.error(f"Failed to save ticket tracker: {e}")
    
    def mark_processed(self, ticket_id: int) -> None:
        """
        Mark a ticket as processed.
        
        Args:
            ticket_id: ID of the ticket to mark as processed.
        """
        self.processed_tickets.add(ticket_id)
        self.save()
    
    def is_processed(self, ticket_id: int) -> bool:
        """
        Check if a ticket has been processed.
        
        Args:
            ticket_id: ID of the ticket to check.
            
        Returns:
            True if the ticket has been processed, False otherwise.
        """
        return ticket_id in self.processed_tickets
    
    def filter_unprocessed_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """
        Filter a list of tickets to only include unprocessed tickets.
        
        Args:
            tickets: List of tickets to filter.
            
        Returns:
            List of unprocessed tickets.
        """
        unprocessed = [t for t in tickets if not self.is_processed(t.id)]
        logger.info(f"Filtered {len(tickets)} tickets to {len(unprocessed)} unprocessed")
        return unprocessed