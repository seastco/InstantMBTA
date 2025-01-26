# InstantMBTA

InstantMBTA is a service for getting the latest MBTA schedules and alerts and displaying them on a Raspberry Pi [Inky pHAT](https://github.com/pimoroni/inky).

This project retrieves the latest train schedules and finds the latest predicted time for inbound and outbound trains, leveraging the [MBTA API](https://github.com/mbta/api).

## Features

- Real-time train schedules and predictions
- Support for both inbound and outbound trains
- Display on Inky pHAT e-ink display
- Configurable for any MBTA route and stops

## Prerequisites

- Raspberry Pi (optional - only needed for display functionality)
- Python 3.x
- Inky pHAT display (optional)
- MBTA API key (get one at [MBTA Portal](https://api-v3.mbta.com/))

## Dependencies

Dependencies are listed in `python/requirements.txt`. Install them using:

```bash
pip install -r python/requirements.txt
```

For NumPy 2.0.0, you'll need OpenBLAS:

```bash
sudo apt-get install libopenblas-dev
```

Note: If you are not using a Raspberry Pi with an Inky display, only the `requests` package is required.

## Usage

### With Raspberry Pi and Inky Display

```bash
python3 instantmbta.py ROUTE_ID "ROUTE_NAME" STOP1_ID "STOP1_NAME" STOP2_ID "STOP2_NAME"
```

### Without Display (Data Collection Only)

```bash
python3 infogather.py ROUTE_ID "ROUTE_NAME" STOP1_ID "STOP1_NAME" STOP2_ID "STOP2_NAME"
```

### Parameters

- `ROUTE_ID`: MBTA route identifier
- `ROUTE_NAME`: Human-readable route name (use quotes if contains spaces)
- `STOP1_ID`: First stop identifier
- `STOP1_NAME`: Human-readable name for first stop (use quotes if contains spaces)
- `STOP2_ID`: Second stop identifier
- `STOP2_NAME`: Human-readable name for second stop (use quotes if contains spaces)

For route and stop IDs, refer to the [MBTA V3 API documentation](https://www.mbta.com/developers/v3-api).

## Example

```bash
python3 instantmbta.py Red "Red Line" place-cntsq "Central Square" place-harsq "Harvard Square"
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

