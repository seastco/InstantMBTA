"""Display mode implementations for different transit tracking scenarios."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from .config_parser import Config, RouteConfig
from .infogather import InfoGather


@dataclass
class TrainPrediction:
    """A single train prediction."""
    time: datetime
    route_name: str
    direction: str  # 'inbound' or 'outbound'
    destination: Optional[str] = None
    uncertainty_minutes: Optional[int] = None


@dataclass
class DisplayLine:
    """A single line of text to display."""
    text: str
    is_header: bool = False
    is_route: bool = False
    indent: bool = False


@dataclass
class DisplayData:
    """Formatted data ready for display."""
    title: str
    date: str
    lines: List[DisplayLine] = field(default_factory=list)
    refresh_seconds: int = 60


class DisplayMode(ABC):
    """Abstract base class for display modes."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f'instantmbta.{self.__class__.__name__}')
    
    @abstractmethod
    def gather_data(self, ig: InfoGather) -> Dict:
        """Gather raw data from MBTA API."""
        pass
    
    @abstractmethod
    def format_for_display(self, data: Dict) -> DisplayData:
        """Format raw data for display."""
        pass
    
    def format_time(self, time_str: Optional[str]) -> str:
        """Convert ISO time string to display format."""
        if not time_str:
            return "---"
        
        try:
            dt = datetime.fromisoformat(time_str)
            if self.config.display.time_format == "24h":
                return dt.strftime("%H:%M")
            else:
                return dt.strftime("%-I:%M %p")
        except Exception:
            return "---"
    
    def abbreviate_route(self, route_name: str) -> str:
        """Abbreviate route name if configured."""
        if not self.config.display.abbreviate:
            return route_name
        
        abbreviations = {
            'Orange Line': 'OL',
            'Red Line': 'RL',
            'Blue Line': 'BL',
            'Green Line': 'GL',
            'Silver Line': 'SL',
        }
        
        # Check for exact match first
        if route_name in abbreviations:
            return abbreviations[route_name]
        
        # Check for commuter rail
        if route_name.endswith(' Line') and route_name.startswith(('Providence', 'Newburyport', 'Framingham', 'Haverhill', 'Fitchburg', 'Worcester', 'Franklin', 'Greenbush', 'Kingston', 'Middleborough', 'Fairmount')):
            return 'CR'
        
        return route_name


class SingleStationMode(DisplayMode):
    """Display mode for tracking multiple routes at a single station."""
    
    def gather_data(self, ig: InfoGather) -> Dict:
        """Gather predictions for all configured routes."""
        data = {
            'station': self.config.station,
            'predictions': [],
            'errors': []
        }
        
        for route in self.config.routes:
            try:
                # Get inbound predictions
                if route.has_inbound:
                    response = ig.get_predictions(self.config.station_id, "0")
                    if response and response.status_code == 200:
                        predictions = self._parse_predictions(
                            response.json(), 
                            route.route_id, 
                            route.route_name,
                            "inbound",
                            route.inbound
                        )
                        data['predictions'].extend(predictions)
                
                # Get outbound predictions
                if route.has_outbound:
                    response = ig.get_predictions(self.config.station_id, "1")
                    if response and response.status_code == 200:
                        predictions = self._parse_predictions(
                            response.json(),
                            route.route_id,
                            route.route_name,
                            "outbound", 
                            route.outbound
                        )
                        data['predictions'].extend(predictions)
                        
            except Exception as e:
                self.logger.error(f"Error getting predictions for {route.route_name}: {e}")
                data['errors'].append(f"{route.route_name}: {str(e)}")
        
        # Sort predictions by time
        data['predictions'].sort(key=lambda p: p.time)
        
        return data
    
    def _parse_predictions(self, response_data: Dict, route_id: str, route_name: str, 
                          direction: str, count: int) -> List[TrainPrediction]:
        """Parse prediction response into TrainPrediction objects."""
        predictions = []
        
        for item in response_data.get('data', []):
            # Check if this prediction is for our route
            relationships = item.get('relationships', {})
            pred_route = relationships.get('route', {}).get('data', {})
            if pred_route.get('id') != route_id:
                continue
            
            attrs = item.get('attributes', {})
            departure_time = attrs.get('departure_time') or attrs.get('arrival_time')
            
            if departure_time and len(predictions) < count:
                predictions.append(TrainPrediction(
                    time=datetime.fromisoformat(departure_time),
                    route_name=route_name,
                    direction=direction,
                    uncertainty_minutes=attrs.get('departure_uncertainty', 120) // 60 if attrs.get('departure_uncertainty') else None
                ))
        
        return predictions
    
    def format_for_display(self, data: Dict) -> DisplayData:
        """Format single station data for display."""
        display = DisplayData(
            title=data['station'],
            date=datetime.now().strftime("%m/%d/%y"),
            refresh_seconds=self.config.display.refresh
        )
        
        # Group predictions by route and direction
        grouped = {}
        for pred in data['predictions']:
            key = (pred.route_name, pred.direction)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(pred)
        
        # Format each group
        for (route_name, direction), preds in grouped.items():
            # Add route header
            abbrev_route = self.abbreviate_route(route_name)
            direction_abbrev = "In" if direction == "inbound" else "Out"
            
            for i, pred in enumerate(preds):
                time_str = self.format_time(pred.time.isoformat())
                if i == 0:
                    # First prediction includes route info
                    line_text = f"{abbrev_route} {direction_abbrev}: {time_str}"
                else:
                    # Subsequent predictions are indented
                    line_text = f"        {time_str}"
                
                display.lines.append(DisplayLine(
                    text=line_text,
                    is_route=(i == 0),
                    indent=(i > 0)
                ))
        
        # Add any errors at the bottom
        for error in data.get('errors', []):
            display.lines.append(DisplayLine(text=f"Error: {error}"))
        
        return display


class MultiStationMode(DisplayMode):
    """Display mode for tracking a journey between two stations."""
    
    def gather_data(self, ig: InfoGather) -> Dict:
        """Gather schedule data for both stations."""
        data = {
            'route': self.config.route_name,
            'from_station': self.config.from_station,
            'to_station': self.config.to_station,
            'from_schedule': None,
            'to_schedule': None,
            'errors': []
        }
        
        try:
            # Get schedule for from station
            from_data = ig.get_current_schedule(
                self.config.route_id,
                self.config.from_station_id
            )
            data['from_schedule'] = {
                'inbound_arrival': from_data[0],
                'outbound_arrival': from_data[1],
                'inbound_departure': from_data[2],
                'outbound_departure': from_data[3]
            }
            
            # Get schedule for to station
            to_data = ig.get_current_schedule(
                self.config.route_id,
                self.config.to_station_id
            )
            data['to_schedule'] = {
                'inbound_arrival': to_data[0],
                'outbound_arrival': to_data[1],
                'inbound_departure': to_data[2],
                'outbound_departure': to_data[3]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting schedule data: {e}")
            data['errors'].append(str(e))
        
        return data
    
    def format_for_display(self, data: Dict) -> DisplayData:
        """Format multi-station data for display."""
        display = DisplayData(
            title=data['route'] if self.config.display.show_route else "",
            date=datetime.now().strftime("%m/%d/%y"),
            refresh_seconds=self.config.display.refresh
        )
        
        # From station
        display.lines.append(DisplayLine(
            text=data['from_station'],
            is_header=True
        ))
        
        if data['from_schedule']:
            # Show inbound time at from station
            inbound_time = self.format_time(data['from_schedule']['inbound_departure'])
            display.lines.append(DisplayLine(
                text=f"Next Inbound:    {inbound_time}",
                indent=False
            ))
        
        # To station
        display.lines.append(DisplayLine(
            text="",  # Blank line
            is_header=False
        ))
        
        display.lines.append(DisplayLine(
            text=data['to_station'],
            is_header=True
        ))
        
        if data['to_schedule']:
            # Show both directions at to station
            inbound_time = self.format_time(data['to_schedule']['inbound_departure'])
            display.lines.append(DisplayLine(
                text=f"Next Inbound:    {inbound_time}",
                indent=False
            ))
            
            outbound_time = self.format_time(data['to_schedule']['outbound_departure'])
            display.lines.append(DisplayLine(
                text=f"Next Outbound:   {outbound_time}",
                indent=False
            ))
        
        # Add any errors
        for error in data.get('errors', []):
            display.lines.append(DisplayLine(text=f"Error: {error}"))
        
        return display


def create_display_mode(config: Config) -> DisplayMode:
    """Factory function to create the appropriate display mode."""
    if config.mode == 'single-station':
        return SingleStationMode(config)
    elif config.mode == 'multi-station':
        return MultiStationMode(config)
    else:
        raise ValueError(f"Unknown display mode: {config.mode}")