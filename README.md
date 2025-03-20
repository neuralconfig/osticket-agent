# OSTicket Network Agent

An AI-powered agent to automatically resolve network-related tickets in osTicket by managing RUCKUS ICX switches.

## Features

- Automatically polls osTicket for new network-related tickets
- Uses AI (Claude 3.5 Haiku) to determine if ticket is within scope
- Supports network operations:
  - Change VLAN on a port
  - Enable/disable a port
  - Enable/disable PoE on a port
- Verifies changes and updates tickets automatically

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Create a `config.ini` file with your osTicket API credentials and switch access information, based on the template in osticket_agent/config.template.ini:

```ini
[osticket]
url = http://your-osticket-url/ost_wbs/
api_key = YOUR_API_KEY_HERE
poll_interval = 60

[openrouter]
api_key = YOUR_OPENROUTER_API_KEY_HERE
model = anthropic/claude-3.5-haiku

[device:switch1]
hostname = 192.168.1.1
username = admin
password = password
device_type = ruckus_fastiron
```

## Usage

Run the agent:

```bash
python -m osticket_agent.main
```

## Testing Switch Operations

Test direct switch operations:

```bash
python test_switch.py --switch SWITCH_NAME --port PORT_ID --operation [status|vlan|poe|set-status|set-vlan|set-poe|all] --value VALUE
```

Test agent tool wrappers:

```bash
python test_network_tools.py --tool [port-status|change-vlan|set-status|set-poe] --switch SWITCH_NAME --port PORT_ID --value VALUE
```

## Development

This project uses:
- Black for formatting
- Flake8 for linting
- MyPy for type checking
- Pytest for testing

## Architecture

- Network operations are handled by SwitchOperation class (osticket_agent/network/switch.py)
- Agent tools wrap these operations for AI use (osticket_agent/agent/tools.py)
- osTicket API client provides ticket management (osticket_agent/api/osticket.py)
- Huggingface's smolagents framework connects the AI to its tools