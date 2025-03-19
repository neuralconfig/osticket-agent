"""Tests for the osTicket API client."""

import json
from datetime import datetime
from unittest import TestCase, mock

import requests
from requests.exceptions import RequestException

from osticket_agent.api.osticket import OSTicketClient, Ticket, TicketStatus


class TestOSTicketClient(TestCase):
    """Tests for the osTicket API client."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = OSTicketClient(
            url="http://test.osticket/api",
            api_key="test_api_key"
        )

    @mock.patch("requests.get")
    def test_get_tickets(self, mock_get):
        """Test getting tickets from the API."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "Success",
            "data": [
                {
                    "id": 1,
                    "number": "100001",
                    "subject": "Test Ticket",
                    "description": "Test ticket description",
                    "status": 1,
                    "status_name": "Open",
                    "created": "2023-01-01T12:00:00",
                    "updated": "2023-01-01T12:30:00",
                    "dept_id": 1,
                    "dept": "Support",
                    "priority_id": 2,
                    "priority": "Normal"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test
        tickets = self.client.get_tickets()
        
        # Verify request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "http://test.osticket/api")
        self.assertEqual(kwargs["headers"]["apikey"], "test_api_key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        
        # Get the payload
        payload = json.loads(kwargs["data"])
        self.assertEqual(payload["query"], "ticket")
        self.assertEqual(payload["condition"], "all")
        self.assertEqual(payload["sort"], "creationDate")
        self.assertIn("parameters", payload)
        self.assertIn("start_date", payload["parameters"])
        self.assertIn("end_date", payload["parameters"])
        
        # Verify response parsing
        self.assertEqual(len(tickets), 1)
        ticket = tickets[0]
        self.assertEqual(ticket.id, 1)
        self.assertEqual(ticket.number, "100001")
        self.assertEqual(ticket.subject, "Test Ticket")
        self.assertEqual(ticket.description, "Test ticket description")
        self.assertEqual(ticket.status_id, 1)
        self.assertEqual(ticket.status_name, "Open")
        self.assertEqual(ticket.department_id, 1)
        self.assertEqual(ticket.department_name, "Support")
        self.assertEqual(ticket.priority_id, 2)
        self.assertEqual(ticket.priority_name, "Normal")
        self.assertTrue(ticket.is_open)
    
    @mock.patch("requests.get")
    def test_get_tickets_with_error(self, mock_get):
        """Test error handling when getting tickets."""
        # Mock response with error
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "Error",
            "data": "API Error"
        }
        mock_get.return_value = mock_response
        
        # Test
        with self.assertRaises(ValueError):
            self.client.get_tickets()
    
    @mock.patch("requests.post")
    def test_reply_to_ticket(self, mock_post):
        """Test replying to a ticket."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "Success",
            "data": "2"
        }
        mock_post.return_value = mock_response
        
        # Test
        result = self.client.reply_to_ticket(1, "Test reply")
        
        # Verify request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://test.osticket/api")
        self.assertEqual(kwargs["headers"]["apikey"], "test_api_key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        
        # Get the payload
        payload = json.loads(kwargs["data"])
        self.assertEqual(payload["query"], "ticket")
        self.assertEqual(payload["condition"], "reply")
        self.assertEqual(payload["parameters"]["ticket_id"], 1)
        self.assertEqual(payload["parameters"]["body"], "<p>Test reply</p>")
        self.assertEqual(payload["parameters"]["staff_id"], 1)
        
        # Verify response
        self.assertTrue(result)
    
    @mock.patch("requests.post")
    def test_close_ticket(self, mock_post):
        """Test closing a ticket."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "Success",
            "data": "3"
        }
        mock_post.return_value = mock_response
        
        # Test
        result = self.client.close_ticket(1, "Closing ticket")
        
        # Verify request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://test.osticket/api")
        self.assertEqual(kwargs["headers"]["apikey"], "test_api_key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        
        # Get the payload
        payload = json.loads(kwargs["data"])
        self.assertEqual(payload["query"], "ticket")
        self.assertEqual(payload["condition"], "close")
        self.assertEqual(payload["parameters"]["ticket_id"], 1)
        self.assertEqual(payload["parameters"]["body"], "<p>Closing ticket</p>")
        self.assertEqual(payload["parameters"]["staff_id"], 1)
        self.assertEqual(payload["parameters"]["status_id"], TicketStatus.CLOSED)
        self.assertEqual(payload["parameters"]["username"], "Network Agent")
        
        # Verify response
        self.assertTrue(result)