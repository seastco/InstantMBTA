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
        
        self.mock_ig.get_predictions_filtered.side_effect = [
            orange_inbound_data,
            orange_outbound_data,
            haverhill_data
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
        self.assertEqual(self.mock_ig.get_predictions_filtered.call_count, 3)
    
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
        self.mock_ig.get_predictions_filtered.side_effect = Exception("API Error")
        
        # Should not raise, but collect errors
        data = mode.gather_data(self.mock_ig)
        
        self.assertEqual(len(data['predictions']), 0)
        self.assertGreater(len(data['errors']), 0)
        self.assertIn('API Error', data['errors'][0])

# Add these test methods to the existing TestDisplayModes class in test_display_modes.py:

    def test_single_station_no_predictions(self):
        """Test handling when no predictions are available."""
        config = self.create_single_station_config()
        mode = SingleStationMode(config)
        
        # Mock empty predictions
        self.mock_ig.get_predictions_filtered.return_value = []
        
        data = mode.gather_data(self.mock_ig)
        
        self.assertEqual(len(data['predictions']), 0)
        self.assertEqual(len(data['errors']), 0)
        
        # Format empty data
        display_data = mode.format_for_display(data)
        self.assertEqual(display_data.title, 'Oak Grove')
        self.assertEqual(len(display_data.lines), 0)  # No predictions to show

    def test_single_station_partial_failures(self):
        """Test when some routes succeed and others fail."""
        config = self.create_single_station_config()
        mode = SingleStationMode(config)
        
        # Mock mixed results - Orange succeeds, Haverhill fails
        orange_predictions = [
            {
                'departure_time': '2025-07-06T10:15:00-04:00',
                'route_id': 'Orange',
                'destination': 'Forest Hills'
            }
        ]
        
        self.mock_ig.get_predictions_filtered.side_effect = [
            orange_predictions,  # Orange inbound success
            [],  # Orange outbound empty
            Exception("Network error")  # Haverhill fails
        ]
        
        data = mode.gather_data(self.mock_ig)
        
        # Should have Orange prediction but error for Haverhill
        self.assertEqual(len(data['predictions']), 1)
        self.assertEqual(len(data['errors']), 1)
        self.assertIn('Haverhill Line', data['errors'][0])

    def test_single_station_time_formatting_edge_cases(self):
        """Test time formatting with various edge cases."""
        config = Config(mode='single-station', display=DisplayConfig(time_format='12h'))
        mode = SingleStationMode(config)
        
        # Test various time edge cases
        test_cases = [
            ('2025-07-06T00:00:00-04:00', '12:00 AM'),  # Midnight
            ('2025-07-06T12:00:00-04:00', '12:00 PM'),  # Noon
            ('2025-07-06T23:59:59-04:00', '11:59 PM'),  # Almost midnight
            ('2025-07-06T01:30:00-04:00', '1:30 AM'),   # Early morning
            (None, '---'),  # None handling
            ('invalid', '---'),  # Invalid format
            ('', '---'),  # Empty string
        ]
        
        for input_time, expected in test_cases:
            result = mode.format_time(input_time)
            self.assertEqual(result, expected, f"Failed for input: {input_time}")

    def test_multi_station_missing_schedule_data(self):
        """Test multi-station mode with missing schedule data."""
        config = self.create_multi_station_config()
        mode = MultiStationMode(config)
        
        # Mock partial schedule data
        self.mock_ig.get_current_schedule.side_effect = [
            (None, None, None, None),  # From station - no data
            ('2025-07-06T10:15:00-04:00', None, '2025-07-06T10:16:00-04:00', None)  # To station - partial
        ]
        
        data = mode.gather_data(self.mock_ig)
        display_data = mode.format_for_display(data)
        
        # Should handle missing data gracefully
        lines_text = [line.text for line in display_data.lines]
        self.assertIn('---', ' '.join(lines_text))  # Missing times shown as ---

    def test_display_line_formatting(self):
        """Test various DisplayLine formatting scenarios."""
        config = self.create_single_station_config()
        mode = SingleStationMode(config)
        
        # Create complex prediction data
        data = {
            'station': 'Wellington',
            'predictions': [
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-06T10:15:00-04:00'),
                    route_name='Orange Line',
                    direction='inbound',
                    destination='Forest Hills'
                ),
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-06T10:18:00-04:00'),
                    route_name='Orange Line',
                    direction='inbound',
                    destination='Forest Hills'
                ),
                TrainPrediction(
                    time=datetime.fromisoformat('2025-07-06T10:20:00-04:00'),
                    route_name='Bus 100',
                    direction='inbound',
                    destination='Downtown'
                ),
            ],
            'errors': ['Test error message']
        }
        
        display_data = mode.format_for_display(data)
        
        # Check line types
        route_lines = [l for l in display_data.lines if l.is_route]
        indented_lines = [l for l in display_data.lines if l.indent]
        error_lines = [l for l in display_data.lines if 'Error:' in l.text]
        
        self.assertEqual(len(route_lines), 2)  # OL and Bus headers
        self.assertEqual(len(indented_lines), 1)  # Second OL prediction
        self.assertEqual(len(error_lines), 1)  # Error message

    def test_abbreviation_edge_cases(self):
        """Test route abbreviation with edge cases."""
        config = Config(mode='single-station', display=DisplayConfig(abbreviate=True))
        mode = SingleStationMode(config)
        
        test_cases = [
            # Standard cases
            ('Orange Line', 'OL'),
            ('Red Line', 'RL'),
            ('Blue Line', 'BL'),
            ('Green Line', 'GL'),
            ('Silver Line', 'SL'),
            
            # Commuter rail
            ('Haverhill Line', 'CR'),
            ('Worcester Line', 'CR'),
            ('Newburyport/Rockport Line', 'CR'),
            
            # Edge cases
            ('Orange', 'Orange'),  # Already abbreviated
            ('Bus 1', 'Bus 1'),  # Bus routes
            ('SL1', 'SL1'),  # Silver Line variant
            ('Green Line B', 'Green Line B'),  # Green Line branch
            ('', ''),  # Empty string
            ('Unknown Route Type', 'Unknown Route Type'),  # Unknown
        ]
        
        for route_name, expected in test_cases:
            result = mode.abbreviate_route(route_name)
            self.assertEqual(result, expected, f"Failed for route: {route_name}")

    def test_config_validation_comprehensive(self):
        """Test comprehensive config validation scenarios."""
        # Test various invalid configurations
        invalid_configs = [
            # Missing required fields
            Config(mode='single-station'),  # No station
            Config(mode='single-station', station='Oak Grove'),  # No routes
            Config(mode='multi-station'),  # No route info
            Config(mode='multi-station', route_id='Red'),  # No stations
            Config(mode='invalid-mode'),  # Invalid mode
        ]
        
        for config in invalid_configs:
            with self.assertRaises(ValueError):
                config.validate()

    def test_predictions_with_uncertainty(self):
        config = self.create_single_station_config()
        mode = SingleStationMode(config)

        # Two inbound, one outbound
        inbound_predictions = [
            {
                'departure_time': '2025-07-06T10:15:00-04:00',
                'route_id': 'Orange',
                'departure_uncertainty': 60,   # 1 minute
            },
            {
                'departure_time': '2025-07-06T10:20:00-04:00',
                'route_id': 'Orange',
                'departure_uncertainty': 300,  # 5 minutes
            },
        ]
        outbound_predictions = [
            {
                'departure_time': '2025-07-06T10:25:00-04:00',
                'route_id': 'Orange',
                'departure_uncertainty': None,  # No uncertainty
            }
        ]

        # gather_data will call get_predictions_filtered twice (dir 0 then dir 1)
        self.mock_ig.get_predictions_filtered.side_effect = [
            inbound_predictions,
            outbound_predictions,
        ]

        data = mode.gather_data(self.mock_ig)

        self.assertEqual(data['predictions'][0].uncertainty_minutes, 1)
        self.assertEqual(data['predictions'][1].uncertainty_minutes, 5)
        self.assertIsNone(data['predictions'][2].uncertainty_minutes)

    def test_display_overflow_scenario(self):
        """Test scenario with too many predictions for display."""
        config = Config(
            mode='single-station',
            station='Park Street',
            station_id='place-pktrm',
            routes=[
                RouteConfig('Red', 'Red Line', inbound=5, outbound=5),
                RouteConfig('Green-B', 'Green Line B', inbound=5, outbound=5),
                RouteConfig('Green-C', 'Green Line C', inbound=5, outbound=5),
            ]
        )
        mode = SingleStationMode(config)
        
        # Mock many predictions
        predictions = []
        for i in range(5):
            predictions.append({
                'departure_time': f'2025-07-06T10:{15+i*5:02d}:00-04:00',
                'route_id': 'Red',
            })
        
        self.mock_ig.get_predictions_filtered.return_value = predictions
        
        data = mode.gather_data(self.mock_ig)
        
        # Even with many routes/predictions requested, should handle gracefully
        self.assertGreaterEqual(len(data['predictions']), 15)  # At least some predictions
        
        # Display formatting should still work
        display_data = mode.format_for_display(data)
        self.assertIsNotNone(display_data)
        self.assertGreater(len(display_data.lines), 0)

if __name__ == '__main__':
    unittest.main()