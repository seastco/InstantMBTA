"""Configuration parser for InstantMBTA - handles YAML configs and CLI backward compatibility."""

import argparse
import yaml
from typing import List, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, field

logger = logging.getLogger('instantmbta.config')


@dataclass
class RouteConfig:
    """Configuration for a single MBTA route to display."""
    route_id: str
    route_name: str
    inbound: int = 0   # Number of inbound trains to show
    outbound: int = 0  # Number of outbound trains to show

    @property
    def has_inbound(self) -> bool:
        return self.inbound > 0

    @property
    def has_outbound(self) -> bool:
        return self.outbound > 0


@dataclass
class DisplayConfig:
    """Display preferences."""
    time_format: str = "12h"
    abbreviate: bool = True
    refresh: int = 60
    show_route: bool = True
    show_directions: bool = False
    minimal: bool = False


@dataclass
class Config:
    """Complete configuration for InstantMBTA."""
    mode: str  # 'single-station' or 'multi-station'

    # Single-station mode
    station: Optional[str] = None
    station_id: Optional[str] = None
    routes: List[RouteConfig] = field(default_factory=list)

    # Multi-station mode
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    from_station: Optional[str] = None
    from_station_id: Optional[str] = None
    to_station: Optional[str] = None
    to_station_id: Optional[str] = None

    # Display settings
    display: DisplayConfig = field(default_factory=DisplayConfig)

    def validate(self):
        if self.mode == 'single-station':
            if not (self.station or self.station_id):
                raise ValueError("Single-station mode requires 'station' or 'station_id'")
            if not self.routes:
                raise ValueError("Single-station mode requires at least one entry under 'routes'")
        elif self.mode == 'multi-station':
            if not self.route_id:
                raise ValueError("Multi-station mode requires 'route'")
            if not (self.from_station or self.from_station_id):
                raise ValueError("Multi-station mode requires 'from' station")
            if not (self.to_station or self.to_station_id):
                raise ValueError("Multi-station mode requires 'to' station")
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


class ConfigParser:
    """Parse configuration from YAML or command line arguments."""

    # Common station name → station ID
    STATION_IDS = {
        'oak grove': 'place-ogmnl',
        'malden center': 'place-mlmnl',
        'wellington': 'place-welln',
        'sullivan square': 'place-sull',
        'community college': 'place-ccmnl',
        'north station': 'place-north',
        'haymarket': 'place-haecl',
        'state street': 'place-state',
        'downtown crossing': 'place-dwnxg',
        'chinatown': 'place-chncl',
        'tufts medical center': 'place-tumnl',
        'back bay': 'place-bbsta',
        'massachusetts avenue': 'place-masta',
        'ruggles': 'place-rugg',
        'roxbury crossing': 'place-rcmnl',
        'jackson square': 'place-jaksn',
        'stony brook': 'place-sbmnl',
        'green street': 'place-grnst',
        'forest hills': 'place-forhl',
        'central square': 'place-cntsq',
        'harvard square': 'place-harsq',
        'porter square': 'place-portr',
        'davis': 'place-davis',
        'alewife': 'place-alfcl',
        'kendall/mit': 'place-knncl',
        'charles/mgh': 'place-chmnl',
        'park street': 'place-pktrm',
        'south station': 'place-sstat',
        'broadway': 'place-brdwy',
        'andrew': 'place-andrw',
        'jfk/umass': 'place-jfkum',
        'ashmont': 'place-asmnl',
        'braintree': 'place-brntn'
    }

    # Common route name → route ID
    ROUTE_IDS = {
        'orange line': 'Orange',
        'orange': 'Orange',
        'ol': 'Orange',
        'red line': 'Red',
        'red': 'Red',
        'rl': 'Red',
        'blue line': 'Blue',
        'blue': 'Blue',
        'bl': 'Blue',
        'green line': 'Green-B,Green-C,Green-D,Green-E',
        'green': 'Green-B,Green-C,Green-D,Green-E',
        'gl': 'Green-B,Green-C,Green-D,Green-E',
        'haverhill line': 'CR-Haverhill',
        'haverhill': 'CR-Haverhill',
        'newburyport/rockport line': 'CR-Newburyport',
        'framingham/worcester line': 'CR-Worcester',
        'providence/stoughton line': 'CR-Providence',
        'franklin/foxboro line': 'CR-Franklin',
    }

    def __init__(self):
        self.logger = logger

    def resolve_station_id(self, station_name: Optional[str]) -> Optional[str]:
        if not station_name:
            return None
        if 'place-' in station_name:
            return station_name
        return self.STATION_IDS.get(station_name.lower().strip(), station_name)

    def resolve_route_id(self, route_name: str) -> str:
        # If it already looks like an API ID, pass through
        if route_name in ['Orange', 'Red', 'Blue'] or route_name.startswith(('Green-', 'CR-')):
            return route_name
        return self.ROUTE_IDS.get(route_name.lower().strip(), route_name)

    def parse_yaml(self, config_path: Path) -> Config:
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ValueError(f"Config file {config_path} not found")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

        # Display settings
        disp = data.get('display', {})
        display = DisplayConfig(
            time_format=disp.get('time_format', '12h'),
            abbreviate=disp.get('abbreviate', True),
            refresh=disp.get('refresh', 60),
            show_route=disp.get('show_route', True),
            show_directions=disp.get('show_directions', False),
            minimal=disp.get('minimal', False),
        )

        mode = data.get('mode', 'single-station').lower()
        config = Config(mode=mode, display=display)

        if mode == 'single-station':
            config.station = data.get('station')
            config.station_id = self.resolve_station_id(config.station)

            for entry in data.get('routes', []):
                if isinstance(entry, dict):
                    for name, rc in entry.items():
                        config.routes.append(RouteConfig(
                            route_id   = self.resolve_route_id(name),
                            route_name = name,
                            inbound    = rc.get('inbound', 0),
                            outbound   = rc.get('outbound', 0),
                        ))

        elif mode == 'multi-station':
            route = data.get('route', '')
            config.route_id   = self.resolve_route_id(route)
            config.route_name = route

            config.from_station    = data.get('from')
            config.from_station_id = self.resolve_station_id(config.from_station)
            config.to_station      = data.get('to')
            config.to_station_id   = self.resolve_station_id(config.to_station)

        config.validate()
        return config

    def parse_cli_args(self, args: argparse.Namespace) -> Config:
        config = Config(mode='multi-station')
        config.route_id        = args.routeid
        config.route_name      = args.routename
        config.from_station    = args.stop1name
        config.from_station_id = args.stop1id
        config.to_station      = args.stop2name
        config.to_station_id   = args.stop2id
        config.validate()
        return config

    def load_config(
        self,
        config_path: Optional[Path] = None,
        cli_args: Optional[argparse.Namespace] = None
    ) -> Config:
        if config_path and config_path.exists():
            self.logger.info(f"Loading config from {config_path}")
            return self.parse_yaml(config_path)

        if cli_args and hasattr(cli_args, 'routeid'):
            self.logger.info("Using legacy CLI arguments")
            return self.parse_cli_args(cli_args)

        for name in ('config.yaml', 'config.yml', 'instantmbta.yaml'):
            p = Path(name)
            if p.exists():
                self.logger.info(f"Loading config from {p}")
                return self.parse_yaml(p)

        raise ValueError("No configuration found. Provide a config file or use CLI arguments.")
