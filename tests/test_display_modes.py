"""Tests for display mode implementations."""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json

from instantmbta.display_modes import (
    create_display_mode, 
    SingleStationMode, 
    MultiStationMode,
    TrainPrediction,
    DisplayData,
    DisplayLine
)
from instantmbta.config_parser import Config, RouteConfig, DisplayConfig


class TestDisplayModes(unittest.TestCase):
    """Test display mode functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ig = Mock()
        
    def create_single_station_config(self):
        """Create a test single-station configuration."""
        return Config(
            mode='single-station',
            station='Oak Grove',
            station_id='place-ogmnl',
            routes=[
                RouteConfig(
                    route_id='Orange',
                    route_name='Orange Line',
                    inbound=2,
                    outbound=1
                ),
                RouteConfig(
                    route_id='CR-Haverhill',
                    route_name='Haverhill Line',
                    inbound=1,
                    outbound=0
                )
            ],
            display=DisplayConfig(time_format='12h', abbreviate=True)
        )
    
    def create_multi_station_config(self):
        """Create a test multi-station configuration."""
        return Config(
            mode='multi-station',
            route_id='Red',
            route_name='Red Line',
            from_station='Central Square',
            from_station_id='place-cntsq',
            to_station='Harvard Square',
            to_station_id='place-harsq',
            display=DisplayConfig(show_route=True)
        )
    
    def create_mock_predictions_response(self, route_id, predictions_data):
        """Create a mock predictions API response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            'data': predictions_data
        }
        return response
    
    def test_create_display_mode_single_station(self):
        """Test factory creates correct mode for single-station."""
        config = self.create_single_station_config()
        mode = create_display_mode(config)
        self.assertIsInstance(mode, SingleStationMode)
    
    def test_create_display_mode_multi_station(self):
        """Test factory creates correct mode for multi-station."""
        config = self.create_multi_station_config()
        mode = create_display_mode(config)
        self.assertIsInstance(mode, MultiStationMode)
    
    def test_create_display_mode_invalid(self):
        """Test factory raises error for invalid mode."""
        config = Config(mode='invalid')
        with self.assertRaises(ValueError):
            create_display_mode(config)
    
    def test_single_station_gather_data(self):
        """Test SingleStationMode data gathering."""
        config = self.create_single_station_config()
        mode = SingleStationMode(config)
        
        # Mock predictions for Orange Line inbound
        orange_inbound_data = [
            {
                'attributes': {
                    'departure_time': '2025-07-05T10:15:00-04:00',
                    'departure_uncertainty': 120
                },
                'relationships': {
                    'route': {'data': {'id': 'Orange'}}
                }
            },
            {
                'attributes': {
                    'departure_time': '2025-07-05T10:23:00-04:00',
                    'departure_uncertainty': 180
                },
                'relationships': {
                    'route': {'data': {'id': 'Orange'}}
                }
            }
        ]
        
        # Mock predictions for Orange Line outbound
        orange_outbound_data = [
            {
                'attributes': {
                    'departure_time': '2025-07-05T10:18:00-04:00',
                    'departure_uncertainty': 60
                },
                'relationships': {
                    'route': {'data': {'id': 'Orange'}}
                }
            }
        ]
        
        # Mock predictions for Haverhill Line
        haverhill_data = [
            {
                'attributes': {
                    'departure_time': '2025-07-05T10:30:00-04:00',
                    'departure_uncertainty': 300
                },
                'relationships': {
                    'route': {'data': {'id': 'CR-Haverhill'}}
                }
            }
        ]
        
        # Set up mock responses
        self.mock_ig.get_predictions.side_effect = [
            self.create_mock_predictions_response('Orange', orange_inbound_data),
            self.create_mock_predictions_response('Orange', orange_outbound_data),
            self.create_mock_predictions_response('CR-Haverhill', haverhill_data)
        ]
        
        # Gather data
        data = mode.gather_data(self.mock_ig)
        
        # Verify results
        self.assertEqual(data['station'], 'Oak Grove')
        self.assertEqual(len(data['predictions']), 4)  # 2 + 1 + 1
        self.assertEqual(len(data['errors']), 0)
        
        # Verify predictions are sorted by time
        times = [p.time for p in data['predictions']]
        self.assertEqual(times, sorted(times))
        
        # Verify API calls
        self.assertEqual(self.mock_ig.get_predictions.call_count, 3)
    
    def test_single_station_format_display(self):
        """Test SingleStationMode display formatting."""
        config = self.create_single_station_config()
        mode = SingleStationMode(config)
        
        # Create test data
        data = {
            'station': 'Oak Grove',
            'predictions': [
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-05T10:15:00-04:00'),
                    route_name='Orange Line',
                    direction='inbound'
                ),
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-05T10:23:00-04:00'),
                    route_name='Orange Line',
                    direction='inbound'
                ),
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-05T10:18:00-04:00'),
                    route_name='Orange Line',
                    direction='outbound'
                ),
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-05T10:30:00-04:00'),
                    route_name='Haverhill Line',
                    direction='inbound'
                )
            ],
            'errors': []
        }
        
        # Format for display
        display_data = mode.format_for_display(data)
        
        # Verify basic structure
        self.assertIsInstance(display_data, DisplayData)
        self.assertEqual(display_data.title, 'Oak Grove')
        self.assertIsNotNone(display_data.date)
        
        # Verify lines
        self.assertGreater(len(display_data.lines), 0)
        
        # Check first Orange Line inbound
        orange_in_lines = [l for l in display_data.lines if 'OL In' in l.text]
        self.assertEqual(len(orange_in_lines), 1)
        self.assertIn('10:15', orange_in_lines[0].text)
        
        # Check Orange Line outbound
        orange_out_lines = [l for l in display_data.lines if 'OL Out' in l.text]
        self.assertEqual(len(orange_out_lines), 1)
        
        # Check Haverhill (should be abbreviated to CR)
        cr_lines = [l for l in display_data.lines if 'CR In' in l.text]
        self.assertEqual(len(cr_lines), 1)
    
    def test_multi_station_gather_data(self):
        """Test MultiStationMode data gathering."""
        config = self.create_multi_station_config()
        mode = MultiStationMode(config)
        
        # Mock schedule responses
        self.mock_ig.get_current_schedule.side_effect = [
            # From station (Central Square)
            (
                '2025-07-05T10:15:00-04:00',  # inbound arrival
                '2025-07-05T10:20:00-04:00',  # outbound arrival
                '2025-07-05T10:16:00-04:00',  # inbound departure
                '2025-07-05T10:21:00-04:00'   # outbound departure
            ),
            # To station (Harvard Square)
            (
                '2025-07-05T10:18:00-04:00',  # inbound arrival
                '2025-07-05T10:25:00-04:00',  # outbound arrival
                '2025-07-05T10:19:00-04:00',  # inbound departure
                '2025-07-05T10:26:00-04:00'   # outbound departure
            )
        ]
        
        # Gather data
        data = mode.gather_data(self.mock_ig)
        
        # Verify results
        self.assertEqual(data['route'], 'Red Line')
        self.assertEqual(data['from_station'], 'Central Square')
        self.assertEqual(data['to_station'], 'Harvard Square')
        self.assertIsNotNone(data['from_schedule'])
        self.assertIsNotNone(data['to_schedule'])
        self.assertEqual(len(data['errors']), 0)
        
        # Verify API calls
        self.assertEqual(self.mock_ig.get_current_schedule.call_count, 2)
        self.mock_ig.get_current_schedule.assert_any_call('Red', 'place-cntsq')
        self.mock_ig.get_current_schedule.assert_any_call('Red', 'place-harsq')
    
    def test_multi_station_format_display(self):
        """Test MultiStationMode display formatting."""
        config = self.create_multi_station_config()
        mode = MultiStationMode(config)
        
        # Create test data
        data = {
            'route': 'Red Line',
            'from_station': 'Central Square',
            'to_station': 'Harvard Square',
            'from_schedule': {
                'inbound_departure': '2025-07-05T10:16:00-04:00'
            },
            'to_schedule': {
                'inbound_departure': '2025-07-05T10:19:00-04:00',
                'outbound_departure': '2025-07-05T10:26:00-04:00'
            },
            'errors': []
        }
        
        # Format for display
        display_data = mode.format_for_display(data)
        
        # Verify basic structure
        self.assertEqual(display_data.title, 'Red Line')
        
        # Find the station headers
        headers = [l for l in display_data.lines if l.is_header]
        self.assertEqual(len(headers), 2)
        self.assertEqual(headers[0].text, 'Central Square')
        self.assertEqual(headers[1].text, 'Harvard Square')
        
        # Check times are formatted correctly
        time_lines = [l for l in display_data.lines if 'Next' in l.text]
        self.assertEqual(len(time_lines), 3)  # 1 at Central, 2 at Harvard
    
    def test_format_time_12h(self):
        """Test time formatting in 12-hour format."""
        config = Config(mode='single-station', display=DisplayConfig(time_format='12h'))
        mode = SingleStationMode(config)
        
        # Morning time
        result = mode.format_time('2025-07-05T10:15:00-04:00')
        self.assertEqual(result, '10:15 AM')
        
        # Afternoon time
        result = mode.format_time('2025-07-05T15:30:00-04:00')
        self.assertEqual(result, '3:30 PM')
        
        # Midnight
        result = mode.format_time('2025-07-05T00:00:00-04:00')
        self.assertEqual(result, '12:00 AM')
        
        # None handling
        result = mode.format_time(None)
        self.assertEqual(result, '---')
    
    def test_format_time_24h(self):
        """Test time formatting in 24-hour format."""
        config = Config(mode='single-station', display=DisplayConfig(time_format='24h'))
        mode = SingleStationMode(config)
        
        result = mode.format_time('2025-07-05T15:30:00-04:00')
        self.assertEqual(result, '15:30')
    
    def test_abbreviate_route(self):
        """Test route name abbreviation."""
        config = Config(mode='single-station', display=DisplayConfig(abbreviate=True))
        mode = SingleStationMode(config)
        
        # Test subway lines
        self.assertEqual(mode.abbreviate_route('Orange Line'), 'OL')
        self.assertEqual(mode.abbreviate_route('Red Line'), 'RL')
        self.assertEqual(mode.abbreviate_route('Blue Line'), 'BL')
        self.assertEqual(mode.abbreviate_route('Green Line'), 'GL')
        
        # Test commuter rail
        self.assertEqual(mode.abbreviate_route('Haverhill Line'), 'CR')
        self.assertEqual(mode.abbreviate_route('Worcester Line'), 'CR')
        
        # Test unknown route
        self.assertEqual(mode.abbreviate_route('Unknown Route'), 'Unknown Route')
    
    def test_error_handling(self):
        """Test error handling in data gathering."""
        config = self.create_single_station_config()
        mode = SingleStationMode(config)
        
        # Mock API error
        self.mock_ig.get_predictions.side_effect = Exception("API Error")
        
        # Should not raise, but collect errors
        data = mode.gather_data(self.mock_ig)
        
        self.assertEqual(len(data['predictions']), 0)
        self.assertGreater(len(data['errors']), 0)
        self.assertIn('API Error', data['errors'][0])


if __name__ == '__main__':
    unittest.main()