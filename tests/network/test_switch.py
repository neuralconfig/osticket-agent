"""Tests for the network switch operations."""

from unittest import TestCase, mock

from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

from osticket_agent.network.switch import SwitchOperation, PortStatus, PoEStatus


class TestSwitchOperation(TestCase):
    """Tests for the SwitchOperation class."""
    
    def setUp(self):
        """Set up test environment."""
        self.switch = SwitchOperation(
            hostname="192.168.1.1",
            username="admin",
            password="password",
            device_type="ruckus_fastiron"
        )
    
    @mock.patch("netmiko.ConnectHandler")
    def test_connect(self, mock_connect):
        """Test connecting to a switch."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connect.return_value = mock_connection
        
        # Test
        self.switch.connect()
        
        # Verify
        mock_connect.assert_called_once_with(
            device_type="ruckus_fastiron",
            host="192.168.1.1",
            username="admin",
            password="password"
        )
        self.assertEqual(self.switch._connection, mock_connection)
    
    @mock.patch("netmiko.ConnectHandler")
    def test_connect_timeout(self, mock_connect):
        """Test handling of connection timeout."""
        # Set up mock
        mock_connect.side_effect = NetmikoTimeoutException("Timeout")
        
        # Test
        with self.assertRaises(NetmikoTimeoutException):
            self.switch.connect()
    
    @mock.patch("netmiko.ConnectHandler")
    def test_connect_auth_failure(self, mock_connect):
        """Test handling of authentication failure."""
        # Set up mock
        mock_connect.side_effect = NetmikoAuthenticationException("Auth failure")
        
        # Test
        with self.assertRaises(NetmikoAuthenticationException):
            self.switch.connect()
    
    @mock.patch("netmiko.ConnectHandler")
    def test_disconnect(self, mock_connect):
        """Test disconnecting from a switch."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connect.return_value = mock_connection
        
        # Connect and then disconnect
        self.switch.connect()
        self.switch.disconnect()
        
        # Verify
        mock_connection.disconnect.assert_called_once()
    
    @mock.patch("netmiko.ConnectHandler")
    def test_execute_command(self, mock_connect):
        """Test executing a command on a switch."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connection.send_command.return_value = "Command output"
        mock_connect.return_value = mock_connection
        
        # Connect and execute command
        self.switch.connect()
        output = self.switch.execute_command("show interfaces")
        
        # Verify
        mock_connection.send_command.assert_called_once_with("show interfaces")
        self.assertEqual(output, "Command output")
    
    @mock.patch("netmiko.ConnectHandler")
    def test_configure(self, mock_connect):
        """Test configuring a switch."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connection.send_config_set.return_value = "Config output"
        mock_connect.return_value = mock_connection
        
        # Connect and configure
        self.switch.connect()
        output = self.switch.configure(["interface ethernet 1/1/1", "enable"])
        
        # Verify
        mock_connection.send_config_set.assert_called_once_with(
            ["interface ethernet 1/1/1", "enable"]
        )
        self.assertEqual(output, "Config output")
    
    @mock.patch("netmiko.ConnectHandler")
    def test_get_port_status(self, mock_connect):
        """Test getting port status."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connection.send_command.return_value = """
        Port 1/1/1 Link: Up State: Forward
        """
        mock_connect.return_value = mock_connection
        
        # Connect and get port status
        self.switch.connect()
        status = self.switch.get_port_status("1/1/1")
        
        # Verify
        mock_connection.send_command.assert_called_once_with("show int br e 1/1/1")
        self.assertEqual(status, PortStatus.ENABLE)
    
    @mock.patch("netmiko.ConnectHandler")
    def test_get_port_vlan(self, mock_connect):
        """Test getting port VLAN."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connection.send_command.return_value = """
        Port 1/1/1 is a member of VLAN 100
        """
        mock_connect.return_value = mock_connection
        
        # Connect and get port VLAN
        self.switch.connect()
        vlan = self.switch.get_port_vlan("1/1/1")
        
        # Verify
        mock_connection.send_command.assert_called_once_with("show vlan br e 1/1/1")
        self.assertEqual(vlan, 100)
    
    @mock.patch("netmiko.ConnectHandler")
    def test_get_poe_status(self, mock_connect):
        """Test getting PoE status."""
        # Set up mock
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connection.send_command.return_value = """
        State: On
        """
        mock_connect.return_value = mock_connection
        
        # Connect and get PoE status
        self.switch.connect()
        status = self.switch.get_poe_status("1/1/1")
        
        # Verify
        mock_connection.send_command.assert_called_once_with("show inline power 1/1/1")
        self.assertEqual(status, PoEStatus.ENABLED)
    
    @mock.patch.object(SwitchOperation, "get_port_vlan")
    @mock.patch.object(SwitchOperation, "configure")
    @mock.patch("netmiko.ConnectHandler")
    def test_change_port_vlan(self, mock_connect, mock_configure, mock_get_vlan):
        """Test changing port VLAN."""
        # Set up mocks
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connect.return_value = mock_connection
        mock_configure.return_value = "Config output"
        mock_get_vlan.return_value = 200  # New VLAN ID
        
        # Connect and change VLAN
        self.switch.connect()
        result = self.switch.change_port_vlan("1/1/1", 200)
        
        # Verify
        mock_configure.assert_called_once_with([
            "vlan 200",
            "untagged ethernet 1/1/1",
            "exit"
        ])
        mock_get_vlan.assert_called_once_with("1/1/1")
        self.assertTrue(result)
    
    @mock.patch.object(SwitchOperation, "get_port_status")
    @mock.patch.object(SwitchOperation, "configure")
    @mock.patch("netmiko.ConnectHandler")
    def test_set_port_status(self, mock_connect, mock_configure, mock_get_status):
        """Test setting port status."""
        # Set up mocks
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connect.return_value = mock_connection
        mock_configure.return_value = "Config output"
        mock_get_status.return_value = PortStatus.ENABLE
        
        # Connect and set port status
        self.switch.connect()
        result = self.switch.set_port_status("1/1/1", PortStatus.ENABLE)
        
        # Verify
        mock_configure.assert_called_once_with([
            "interface ethernet 1/1/1",
            "enable",
            "exit"
        ])
        mock_get_status.assert_called_once_with("1/1/1")
        self.assertTrue(result)
    
    @mock.patch.object(SwitchOperation, "get_poe_status")
    @mock.patch.object(SwitchOperation, "configure")
    @mock.patch("netmiko.ConnectHandler")
    def test_set_poe_status(self, mock_connect, mock_configure, mock_get_status):
        """Test setting PoE status."""
        # Set up mocks
        mock_connection = mock.Mock()
        mock_connection.is_alive.return_value = True
        mock_connect.return_value = mock_connection
        mock_configure.return_value = "Config output"
        mock_get_status.return_value = PoEStatus.ENABLED
        
        # Connect and set PoE status
        self.switch.connect()
        result = self.switch.set_poe_status("1/1/1", PoEStatus.ENABLED)
        
        # Verify
        mock_configure.assert_called_once_with([
            "interface ethernet 1/1/1",
            "inline power",
            "exit"
        ])
        mock_get_status.assert_called_once_with("1/1/1")
        self.assertTrue(result)