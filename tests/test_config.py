"""Tests for the configuration module."""

import os
import tempfile
from unittest import TestCase, mock

from osticket_agent.config import load_config, Config, OSTicketConfig, NetworkDeviceConfig


class TestConfig(TestCase):
    """Tests for the configuration module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary config file
        self.config_file = tempfile.NamedTemporaryFile(delete=False)
        self.config_file.write(b"""
[osticket]
url = http://test.osticket/api/
api_key = test_api_key
poll_interval = 30

[openrouter]
api_key = test_openrouter_key
model = anthropic/claude-3-haiku

[device:switch1]
hostname = 192.168.1.1
username = admin
password = password
device_type = ruckus_fastiron

[device:switch2]
hostname = 192.168.1.2
username = admin2
password = password2
        """)
        self.config_file.close()
    
    def tearDown(self):
        """Clean up after tests."""
        os.unlink(self.config_file.name)
    
    def test_load_config(self):
        """Test loading configuration from file."""
        config = load_config(self.config_file.name)
        
        # Check osTicket config
        self.assertEqual(config.osticket.url, "http://test.osticket/api/")
        self.assertEqual(config.osticket.api_key, "test_api_key")
        self.assertEqual(config.osticket.poll_interval, 30)
        
        # Check OpenRouter config
        self.assertEqual(config.openrouter_api_key, "test_openrouter_key")
        self.assertEqual(config.model, "anthropic/claude-3-haiku")
        
        # Check network devices
        self.assertEqual(len(config.network_devices), 2)
        self.assertIn("switch1", config.network_devices)
        self.assertIn("switch2", config.network_devices)
        
        # Check switch1 config
        switch1 = config.network_devices["switch1"]
        self.assertEqual(switch1.hostname, "192.168.1.1")
        self.assertEqual(switch1.username, "admin")
        self.assertEqual(switch1.password, "password")
        self.assertEqual(switch1.device_type, "ruckus_fastiron")
        
        # Check switch2 config
        switch2 = config.network_devices["switch2"]
        self.assertEqual(switch2.hostname, "192.168.1.2")
        self.assertEqual(switch2.username, "admin2")
        self.assertEqual(switch2.password, "password2")
        self.assertEqual(switch2.device_type, "ruckus_fastiron")  # Default value
    
    def test_missing_config_file(self):
        """Test handling of missing config file."""
        with self.assertRaises(FileNotFoundError):
            load_config("nonexistent_file.ini")
    
    @mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "env_api_key"})
    def test_environment_variables(self):
        """Test loading API key from environment variables."""
        # Create a config without API key
        with tempfile.NamedTemporaryFile(delete=False) as config_file:
            config_file.write(b"""
[osticket]
url = http://test.osticket/api/
api_key = test_api_key

[device:switch1]
hostname = 192.168.1.1
username = admin
password = password
            """)
            config_file.close()
            
            try:
                config = load_config(config_file.name)
                self.assertEqual(config.openrouter_api_key, "env_api_key")
            finally:
                os.unlink(config_file.name)