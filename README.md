# OSTicket Network Agent

An AI-powered agent to automatically resolve network-related tickets in osTicket by managing RUCKUS ICX switches.

## Features

- Automatically polls osTicket for new network-related tickets
- Uses AI to determine if ticket is within scope
- Supports operations:
  - Change VLAN on a port
  - Enable/disable a port
  - Enable/disable PoE on a port
- Verifies changes and updates tickets

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Create a `config.ini` file with your osTicket API credentials and switch access information.

## Usage

```bash
python -m osticket_agent.main
```

## Development

This project uses:
- Black for formatting
- Flake8 for linting
- MyPy for type checking
- Pytest for testing