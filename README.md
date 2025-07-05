# InstantMBTA

InstantMBTA is a real-time MBTA transit display that shows train schedules and predictions on a Raspberry Pi [Inky pHAT](https://github.com/pimoroni/inky) e-ink display. Perfect for placing near your door to check train times before leaving home.

## Features

- **Multiple Display Modes**: Station arrivals, journey tracking, or bidirectional views
- **Multi-Route Support**: Track trains from different lines at the same station
- **Real-time Updates**: Live predictions from the MBTA API
- **Flexible Configuration**: YAML config files for easy customization
- **E-ink Display**: Low power, always-on display (optional)
- **Smart Station Resolution**: Use friendly names like "Oak Grove" instead of IDs

## Installation

1. Clone the repository:
```bash
git clone https://github.com/seastco/InstantMBTA.git
cd InstantMBTA
```

2. Install dependencies:
```bash
cd python
pip install -r requirements.txt
```

For Raspberry Pi with display:
```bash
sudo apt-get install libopenblas-dev  # Required for NumPy 2.0.0
```

3. Set up your API key:
```bash
# Create python/secret_constants.py
echo 'API_KEY = "your-api-key-here"' > python/secret_constants.py
```

## Quick Start

1. Copy the example config:
```bash
cp example_config.yaml config.yaml
```

2. Edit `config.yaml` for your needs (see modes below)

3. Run InstantMBTA:
```bash
python3 instantmbta.py
```

## Display Modes

### Station Mode
Track multiple routes at your home station:

```yaml
# config.yaml
mode: station
station: Oak Grove

track:
  - Orange Line:
      direction: inbound
      count: 2
  
  - Haverhill Line:
      direction: inbound
      count: 1

display:
  time_format: 12h
  abbreviate: true
```

**Display Output:**
```
Oak Grove           07/04/25

OL In:  10:15 AM
OL In:  10:23 AM
CR In:  10:28 AM
```

### Bidirectional Mode
Great for stations where you travel in both directions:

```yaml
mode: bidirectional
station: Central Square
route: Red Line

inbound:
  show: 2

outbound:
  show: 2

display:
  show_directions: true
```

**Display Output:**
```
Central Square      07/04/25

← Alewife
  10:15 AM
  10:23 AM
→ Ashmont/Braintree
  10:14 AM
  10:21 AM
```

### Journey Mode
Track your regular commute between two stations:

```yaml
mode: journey
route: Red Line
from: Central Square
to: Harvard Square

display:
  show_route: true
```

**Display Output:**
```
Red Line            07/04/25

Central Square
Next Inbound:    10:15 AM

Harvard Square  
Next Inbound:    10:18 AM
Next Outbound:   10:22 AM
```

## Configuration Reference

### Station Names
Use friendly names - they're automatically converted:
- `Oak Grove` → place-ogmnl
- `Central Square` → place-cntsq  
- `North Station` → place-north
- `Park Street` → place-pktrm

### Route Names
Use any common format:
- `Orange Line`, `Orange`, or `OL` → Orange
- `Red Line`, `Red`, or `RL` → Red
- `Haverhill Line` or `Haverhill` → CR-Haverhill

### Display Options
```yaml
display:
  time_format: 12h      # 12h or 24h
  abbreviate: true      # OL vs Orange Line
  refresh: 60           # seconds between updates
  show_directions: true # show arrows for bidirectional
  minimal: false        # minimal display mode
```

## Command Line Usage

### With Config File (Recommended)
```bash
# Use default config.yaml
python3 instantmbta.py

# Use specific config
python3 instantmbta.py --config morning-commute.yaml

# Run once for testing
python3 instantmbta.py --once

# Debug mode
python3 instantmbta.py --log-level DEBUG
```

### Legacy CLI Mode
For backward compatibility or quick tests:
```bash
python3 instantmbta.py Red "Red Line" place-cntsq "Central Square" place-harsq "Harvard Square"
```

### Data Only (No Display)
```bash
python3 infogather.py --config config.yaml
```

## Examples

### Home Station with Multiple Lines
```yaml
mode: station
station: North Station
track:
  - Orange Line:
      direction: outbound
      count: 3
  - Green Line:
      direction: outbound  
      count: 2
  - Haverhill Line:
      direction: outbound
      count: 1
```

### Flexible Commute Station
```yaml
mode: bidirectional
station: Harvard Square
route: Red Line
inbound:
  show: 3
outbound:
  show: 3
```

### Evening Commute Tracker
```yaml
mode: journey
route: Orange Line
from: Downtown Crossing
to: Oak Grove
display:
  time_format: 24h  # 17:30 instead of 5:30 PM
```

## Advanced Usage

### Multiple Configurations
Create different configs for different use cases:
```bash
# Morning commute
python3 instantmbta.py --config morning.yaml

# Evening commute  
python3 instantmbta.py --config evening.yaml

# Weekend trips
python3 instantmbta.py --config weekend.yaml
```

### Testing Your Configuration
```bash
# Validate config and run once
python3 instantmbta.py --config myconfig.yaml --once

# See what API calls are being made
python3 instantmbta.py --log-level DEBUG
```

## Troubleshooting

**No display output**: Ensure you're running on a Raspberry Pi with Inky pHAT installed

**Config not found**: Check that config.yaml exists in the python directory

**Station not recognized**: Use quotes around station names with spaces: `station: "Oak Grove"`

**No predictions found**: Some stations/routes have limited service - check MBTA.com

**API rate limits**: The built-in circuit breaker will automatically retry failed requests

## Logging

- Continuous mode: Logs to `instant.log` (rotating, max 2MB)
- One-time mode (`--once`): Logs to console
- Debug mode shows API calls and responses
