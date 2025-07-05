"""Configuration parser for InstantMBTA - handles YAML configs and CLI backward compatibility."""

import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
from dataclasses import dataclass, field

logger = logging.getLogger('instantmbta.config')


@dataclass
class RouteConfig:
    """Configuration for a single route to track."""
    route_id: str
    route_name: str
    direction: str  # 'inbound' or 'outbound'
    count: int = 1
    
    @property
    def direction_id(self) -> str:
        """Convert direction name to MBTA API direction ID."""
        return "0" if self.direction.lower() == "inbound" else "1"


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
    mode: str
    
    # Station mode / bi-directional mode
    station: Optional[str] = None
    station_id: Optional[str] = None
    tracks: List[RouteConfig] = field(default_factory=list)
    
    # Journey mode
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    from_station: Optional[str] = None
    from_station_id: Optional[str] = None
    to_station: Optional[str] = None
    to_station_id: Optional[str] = None
    
    # Bi-directional specific
    inbound_count: int = 2
    outbound_count: int = 2
    
    # Display settings
    display: DisplayConfig = field(default_factory=DisplayConfig)
    
    def validate(self):
        """Validate configuration based on mode."""
        if self.mode == 'station':
            if not self.station and not self.station_id:
                raise ValueError("Station mode requires 'station' or 'station_id'")
            if not self.tracks:
                raise ValueError("Station mode requires at least one route in 'track'")
                
        elif self.mode == 'journey':
            if not self.route_id:
                raise ValueError("Journey mode requires 'route'")
            if not (self.from_station or self.from_station_id):
                raise ValueError("Journey mode requires 'from' station")
            if not (self.to_station or self.to_station_id):
                raise ValueError("Journey mode requires 'to' station")
                
        elif self.mode == 'bidirectional':
            if not self.station and not self.station_id:
                raise ValueError("Bidirectional mode requires 'station'")
            if not self.tracks or len(self.tracks) != 1:
                raise ValueError("Bidirectional mode requires exactly one route in 'track'")
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


class ConfigParser:
    """Parse configuration from YAML or command line arguments."""
    
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
        """Convert station name to ID."""
        if not station_name:
            return None
        
        # If it already looks like an ID (contains 'place-'), return as-is
        if 'place-' in station_name:
            return station_name
            
        # Try to find in mapping
        normalized = station_name.lower().strip()
        return self.STATION_IDS.get(normalized, station_name)
    
    def resolve_route_id(self, route_name: str) -> str:
        """Convert route name to ID."""
        # If it already looks like an ID, return as-is
        if route_name in ['Orange', 'Red', 'Blue'] or route_name.startswith('Green-') or route_name.startswith('CR-'):
            return route_name
            
        # Try to find in mapping
        normalized = route_name.lower().strip()
        return self.ROUTE_IDS.get(normalized, route_name)
    
    def parse_yaml(self, config_path: Path) -> Config:
        """Parse configuration from YAML file."""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Parse display settings
        display_data = data.get('display', {})
        display = DisplayConfig(
            time_format=display_data.get('time_format', '12h'),
            abbreviate=display_data.get('abbreviate', True),
            refresh=display_data.get('refresh', 60),
            show_route=display_data.get('show_route', True),
            show_directions=display_data.get('show_directions', False),
            minimal=display_data.get('minimal', False)
        )
        
        # Get mode
        mode = data.get('mode', 'station').lower()
        
        # Initialize config
        config = Config(mode=mode, display=display)
        
        # Parse based on mode
        if mode == 'station':
            config.station = data.get('station')
            config.station_id = self.resolve_station_id(config.station)
            
            # Parse tracks
            tracks_data = data.get('track', [])
            for track in tracks_data:
                if isinstance(track, dict):
                    for route_name, route_config in track.items():
                        route_id = self.resolve_route_id(route_name)
                        config.tracks.append(RouteConfig(
                            route_id=route_id,
                            route_name=route_name,
                            direction=route_config.get('direction', 'inbound'),
                            count=route_config.get('count', 1)
                        ))
        
        elif mode == 'journey':
            route = data.get('route', '')
            config.route_id = self.resolve_route_id(route)
            config.route_name = route
            config.from_station = data.get('from')
            config.from_station_id = self.resolve_station_id(config.from_station)
            config.to_station = data.get('to')
            config.to_station_id = self.resolve_station_id(config.to_station)
        
        elif mode == 'bidirectional':
            config.station = data.get('station')
            config.station_id = self.resolve_station_id(config.station)
            
            route = data.get('route', '')
            route_id = self.resolve_route_id(route)
            
            # Create track configs for both directions
            inbound_data = data.get('inbound', {})
            outbound_data = data.get('outbound', {})
            
            config.inbound_count = inbound_data.get('show', 2)
            config.outbound_count = outbound_data.get('show', 2)
            
            # Store as single track with both directions noted
            config.tracks.append(RouteConfig(
                route_id=route_id,
                route_name=route,
                direction='both',  # Special case for bidirectional
                count=max(config.inbound_count, config.outbound_count)
            ))
        
        config.validate()
        return config
    
    def parse_cli_args(self, args: argparse.Namespace) -> Config:
        """Create config from legacy CLI arguments for backward compatibility."""
        # Legacy mode is always journey mode
        config = Config(mode='journey')
        
        config.route_id = args.routeid
        config.route_name = args.routename
        config.from_station = args.stop1name
        config.from_station_id = args.stop1id
        config.to_station = args.stop2name
        config.to_station_id = args.stop2id
        
        config.validate()
        return config
    
    def load_config(self, config_path: Optional[Path] = None, 
                   cli_args: Optional[argparse.Namespace] = None) -> Config:
        """Load configuration from file or CLI args."""
        if config_path and config_path.exists():
            self.logger.info(f"Loading config from {config_path}")
            return self.parse_yaml(config_path)
        elif cli_args and hasattr(cli_args, 'routeid'):
            self.logger.info("Using legacy CLI arguments")
            return self.parse_cli_args(cli_args)
        else:
            # Look for default config file
            default_configs = ['config.yaml', 'config.yml', 'instantmbta.yaml']
            for cfg in default_configs:
                cfg_path = Path(cfg)
                if cfg_path.exists():
                    self.logger.info(f"Loading config from {cfg_path}")
                    return self.parse_yaml(cfg_path)
            
            raise ValueError("No configuration found. Provide a config file or use CLI arguments.")