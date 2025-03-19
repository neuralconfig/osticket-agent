"""AI agent for network ticket resolution."""

import logging
import time
from typing import Dict, List, Optional, Any

import openai
from smolagents.runner.agent import Agent

from osticket_agent.api.osticket import Ticket, OSTicketClient
from osticket_agent.api.ticket_tracker import TicketTracker
from osticket_agent.agent.tools import get_network_tools
from osticket_agent.network.switch import SwitchOperation

# Set up logging
logger = logging.getLogger(__name__)


class NetworkAgent:
    """AI agent for resolving network tickets."""
    
    def __init__(
        self,
        osticket_client: OSTicketClient,
        openrouter_api_key: str,
        switches: Dict[str, SwitchOperation],
        model: str,
        ticket_tracker: Optional[TicketTracker] = None
    ):
        """
        Initialize the network agent.
        
        Args:
            osticket_client: OSTicketClient instance.
            openrouter_api_key: OpenRouter API key.
            switches: Dictionary of switch name to SwitchOperation instance.
            model: OpenRouter model to use.
            ticket_tracker: TicketTracker instance (creates one if None).
        """
        self.osticket_client = osticket_client
        self.openrouter_api_key = openrouter_api_key
        self.switches = switches
        self.model = model
        self.ticket_tracker = ticket_tracker or TicketTracker()
        
        # Configure OpenAI client for OpenRouter
        openai.api_key = openrouter_api_key
        openai.base_url = "https://openrouter.ai/api/v1"
        
        # Set up the AI agent
        self.tools = get_network_tools(osticket_client, switches)
        self.system_message = """
        You are a network assistant that helps resolve tickets related to network issues.
        
        You can perform the following tasks:
        1. Change VLAN on a port
        2. Enable or disable a port
        3. Enable or disable PoE on a port
        
        When given a ticket, analyze it to determine if it's within your scope.
        If it is, use your tools to make the requested changes, verify them, and close the ticket.
        If it's not within your scope, explain why and do not make any changes.
        
        When replying to tickets, be professional and concise. Explain what changes you made
        and any verification steps you took.
        """
    
    def _create_agent(self) -> Agent:
        """
        Create an AI agent with tools.
        
        Returns:
            SmolaGents Agent instance.
        """
        return Agent(
            provider="openai",
            model=self.model,
            tools=self.tools,
            system_message=self.system_message,
        )
    
    def process_ticket(self, ticket: Ticket) -> bool:
        """
        Process a single ticket.
        
        Args:
            ticket: Ticket to process.
            
        Returns:
            True if the ticket was successfully processed, False otherwise.
        """
        logger.info(f"Processing ticket {ticket.id}: {ticket.subject}")
        logger.debug(f"Ticket details: ID={ticket.id}, Number={ticket.number}, Subject='{ticket.subject}', Status={ticket.status_name}")
        logger.debug(f"Ticket description: {ticket.description}")
        
        # Skip if already processed
        if self.ticket_tracker.is_processed(ticket.id):
            logger.info(f"Ticket {ticket.id} already processed, skipping")
            return True
        
        # Get agent
        agent = self._create_agent()
        logger.debug(f"Created AI agent with model: {self.model}")
        
        # First, ask the agent to analyze the ticket
        analysis_prompt = f"""
        You need to determine if this ticket is within your scope to handle.
        
        Ticket ID: {ticket.id}
        Subject: {ticket.subject}
        Description: {ticket.description}
        
        Is this ticket requesting any of the following operations?
        1. Change VLAN on a port
        2. Enable or disable a port
        3. Enable or disable PoE on a port
        
        If it is, extract the following information:
        - The switch name
        - The port number
        - The requested operation
        - Any specific parameters (like VLAN ID)
        
        If it's not within your scope, explain why.
        """
        
        try:
            logger.debug(f"Sending analysis prompt to AI agent")
            analysis_response = agent.run(analysis_prompt)
            logger.debug(f"Analysis response from AI: {analysis_response}")
            
            # If the agent determines the ticket is not in scope, mark as processed
            if "not within" in analysis_response.lower() or "out of scope" in analysis_response.lower():
                logger.info(f"Ticket {ticket.id} determined to be out of scope, marking as processed")
                self.ticket_tracker.mark_processed(ticket.id)
                
                # Reply to the ticket indicating it's not in scope
                logger.debug(f"Replying to ticket {ticket.id} indicating it's out of scope")
                reply_success = self.osticket_client.reply_to_ticket(
                    ticket.id,
                    f"This ticket is not within the scope of automated network operations: {analysis_response}"
                )
                logger.debug(f"Reply to ticket {ticket.id} success: {reply_success}")
                return True
            
            # Otherwise, ask the agent to process the ticket
            logger.info(f"Ticket {ticket.id} is in scope, proceeding with processing")
            process_prompt = f"""
            You've determined that ticket {ticket.id} is within your scope.
            
            Now, complete the following steps:
            1. Use your tools to perform the requested operation
            2. Verify that the operation was successful
            3. Reply to the ticket with the results
            4. If successful, close the ticket
            
            Be sure to handle any errors that occur during the process.
            """
            
            logger.debug(f"Sending processing prompt to AI agent for ticket {ticket.id}")
            process_response = agent.run(process_prompt)
            logger.debug(f"Process response from AI for ticket {ticket.id}: {process_response}")
            
            # Mark the ticket as processed regardless of outcome
            logger.info(f"Marking ticket {ticket.id} as processed")
            self.ticket_tracker.mark_processed(ticket.id)
            return True
        
        except Exception as e:
            logger.error(f"Error processing ticket {ticket.id}: {e}", exc_info=True)
            logger.debug(f"Exception details for ticket {ticket.id}: {type(e).__name__}: {str(e)}")
            return False
    
    def run(self, poll_interval: int = 60) -> None:
        """
        Run the agent to process tickets.
        
        Args:
            poll_interval: Interval in seconds to poll for new tickets.
        """
        logger.info(f"Starting network agent with poll interval {poll_interval}s")
        logger.info(f"Using AI model: {self.model}")
        logger.info(f"Configured switches: {', '.join(self.switches.keys())}")
        
        try:
            while True:
                try:
                    logger.debug("Polling for new tickets...")
                    # Get open tickets
                    tickets = self.osticket_client.get_tickets()
                    logger.debug(f"Retrieved {len(tickets)} tickets from osTicket")
                    
                    # Filter to unprocessed tickets
                    unprocessed_tickets = self.ticket_tracker.filter_unprocessed_tickets(tickets)
                    if unprocessed_tickets:
                        logger.info(f"Found {len(unprocessed_tickets)} unprocessed tickets to process")
                    else:
                        logger.debug("No new tickets to process")
                    
                    # Process each ticket
                    for ticket in unprocessed_tickets:
                        logger.debug(f"Processing ticket {ticket.id}...")
                        success = self.process_ticket(ticket)
                        logger.debug(f"Ticket {ticket.id} processing {'succeeded' if success else 'failed'}")
                
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                
                # Wait for next poll
                logger.debug(f"Sleeping for {poll_interval}s until next poll")
                time.sleep(poll_interval)
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")