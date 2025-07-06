# InstantMBTA

InstantMBTA is a real-time MBTA transit display that shows train schedules and predictions on a Raspberry Pi [Inky pHAT](https://github.com/pimoroni/inky) e-ink display. Perfect for placing near your door to check train times before leaving home!

## Features

- **Multiple Display Modes**: Station arrivals or journey tracking
- **Multi-Route Support**: Track trains from different lines at the same station
- **Real-time Updates**: Live predictions from the MBTA API
- **Flexible Configuration**: YAML config files for easy customization
- **E-ink Display**: Low power, always-on display (optional)
- **Smart Station Resolution**: Use friendly names like "Oak Grove" instead of IDs

## Requirements

- Python 3.13 or higher
- Raspberry Pi with Inky pHAT display (optional - can run in console mode)
- MBTA API key (free from [MBTA V3 API](https://www.mbta.com/developers/v3-api))

## Installation

1. Clone the repository:
```bash
git clone git@github.com:seastco/InstantMBTA.git
cd InstantMBTA
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

For Raspberry Pi with display:
```bash
sudo apt-get install libopenblas-dev  # Required for NumPy
```

3. Set up your API key:
```bash
# Get your free API key from https://api-v3.mbta.com/
echo 'API_KEY = "your-api-key-here"' > instantmbta/secret_constants.py
```

## Quick Start

1. Copy an example config:
```bash
cp examples/config_single_station.yaml config.yaml
```

2. Edit `config.yaml` for your station

3. Run InstantMBTA:
```bash
# Test without display (console output)
python3 -m instantmbta --config config.yaml --once

# Run continuously with display
python3 -m instantmbta --config config.yaml
```

## Configuration

### Single-Station Mode
Track multiple routes at your home station:

```yaml
mode: single-station
station: Oak Grove

routes:
  - Orange Line:
      inbound: 2    # Next 2 trains inbound
  - Haverhill Line:
      inbound: 1    # Next commuter rail

display:
  time_format: 12h
  abbreviate: true  # OL instead of Orange Line
  refresh: 60       # Update every 60 seconds
```

### Multi-Station Mode (Journey)
Track your commute between two stations:

```yaml
mode: multi-station
route: Red Line
from: Central Square
to: Harvard Square

display:
  show_route: true
```

### Station & Route Names
Use friendly names - they're automatically converted:
- `Oak Grove` → place-ogmnl
- `Central Square` → place-cntsq  
- `Orange Line` or `OL` → Orange
- `Haverhill Line` → CR-Haverhill

See [MBTA API documentation](https://www.mbta.com/developers/v3-api) for all station and route IDs.

## Command Line Usage

```bash
# Use config file
python3 -m instantmbta --config config.yaml

# Test mode (run once)
python3 -m instantmbta --config config.yaml --once

# Debug mode
python3 -m instantmbta --config config.yaml --log-level DEBUG
```

## Display Output Examples

### Single-Station Mode
```
Oak Grove           07/06/25

OL In:  10:15 AM
OL In:  10:23 AM
CR In:  10:28 AM
```

### Multi-Station Mode
```
Red Line            07/06/25

Central Square
Next Inbound:    10:15 AM

Harvard Square  
Next Inbound:    10:18 AM
Next Outbound:   10:22 AM
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Project Structure
```
instantmbta/
├── instantmbta/
│   ├── __main__.py       # Entry point
│   ├── config_parser.py  # YAML configuration parser
│   ├── display_modes.py  # Display mode implementations
│   ├── infogather.py     # MBTA API client
│   └── inkytrain.py      # E-ink display driver
├── examples/             # Example configurations
├── tests/               # Unit tests
└── config.yaml          # Your configuration (create this)
```

## Troubleshooting

**No display output**: Ensure you're running on a Raspberry Pi with Inky pHAT installed

**"API key not found"**: Create `instantmbta/secret_constants.py` with your MBTA API key

**"Station not recognized"**: Check spelling and try the full name (e.g., "Oak Grove" not "Oak")

**No predictions**: Some stations/routes have limited service. Check [MBTA.com](https://www.mbta.com)

**Display overflow**: Reduce the number of predictions in your config