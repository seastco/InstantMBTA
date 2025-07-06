"""Tests for the configuration parser."""

import unittest
import tempfile
import yaml
from pathlib import Path
from instantmbta.config_parser import ConfigParser, Config


class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.parser = ConfigParser()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def write_config(self, filename: str, config_dict: dict) -> Path:
        """Helper to write a test config file."""
        config_path = self.temp_path / filename
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f)
        return config_path
    
    def test_single_station_mode_config(self):
        """Test parsing single-station mode configuration."""
        config_dict = {
            'mode': 'single-station',
            'station': 'Oak Grove',
            'routes': [
                {'Orange Line': {'inbound': 2}},
                {'Haverhill Line': {'inbound': 1}}
            ],
            'display': {
                'time_format': '12h',
                'abbreviate': True,
                'refresh': 60
            }
        }
        
        config_path = self.write_config('single_station_test.yaml', config_dict)
        config = self.parser.parse_yaml(config_path)
        
        # Verify basic settings
        self.assertEqual(config.mode, 'single-station')
        self.assertEqual(config.station, 'Oak Grove')
        self.assertEqual(config.station_id, 'place-ogmnl')
        
        # Verify routes
        self.assertEqual(len(config.routes), 2)
        
        orange_route = config.routes[0]
        self.assertEqual(orange_route.route_id, 'Orange')
        self.assertEqual(orange_route.route_name, 'Orange Line')
        self.assertEqual(orange_route.inbound, 2)
        self.assertEqual(orange_route.outbound, 0)
        self.assertTrue(orange_route.has_inbound)
        self.assertFalse(orange_route.has_outbound)
        
        haverhill_route = config.routes[1]
        self.assertEqual(haverhill_route.route_id, 'CR-Haverhill')
        self.assertEqual(haverhill_route.route_name, 'Haverhill Line')
        self.assertEqual(haverhill_route.inbound, 1)
        
        # Verify display settings
        self.assertEqual(config.display.time_format, '12h')
        self.assertTrue(config.display.abbreviate)
        self.assertEqual(config.display.refresh, 60)
    
    def test_multi_station_mode_config(self):
        """Test parsing multi-station mode configuration."""
        config_dict = {
            'mode': 'multi-station',
            'route': 'Red Line',
            'from': 'Central Square',
            'to': 'Harvard Square',
            'display': {
                'show_route': True,
                'time_format': '24h'
            }
        }
        
        config_path = self.write_config('multi_station_test.yaml', config_dict)
        config = self.parser.parse_yaml(config_path)
        
        self.assertEqual(config.mode, 'multi-station')
        self.assertEqual(config.route_id, 'Red')
        self.assertEqual(config.route_name, 'Red Line')
        self.assertEqual(config.from_station, 'Central Square')
        self.assertEqual(config.from_station_id, 'place-cntsq')
        self.assertEqual(config.to_station, 'Harvard Square')
        self.assertEqual(config.to_station_id, 'place-harsq')
        self.assertTrue(config.display.show_route)
        self.assertEqual(config.display.time_format, '24h')
    
    def test_single_station_bidirectional_config(self):
        """Test parsing single-station mode with both directions."""
        config_dict = {
            'mode': 'single-station',
            'station': 'Central Square',
            'routes': [
                {'Red Line': {'inbound': 3, 'outbound': 2}}
            ]
        }
        
        config_path = self.write_config('bidir_test.yaml', config_dict)
        config = self.parser.parse_yaml(config_path)
        
        self.assertEqual(config.mode, 'single-station')
        self.assertEqual(config.station_id, 'place-cntsq')
        self.assertEqual(len(config.routes), 1)
        
        route = config.routes[0]
        self.assertEqual(route.route_id, 'Red')
        self.assertEqual(route.inbound, 3)
        self.assertEqual(route.outbound, 2)
        self.assertTrue(route.has_inbound)
        self.assertTrue(route.has_outbound)
    
    def test_station_name_resolution(self):
        """Test station name to ID resolution."""
        # Test various formats
        test_cases = [
            ('Oak Grove', 'place-ogmnl'),
            ('oak grove', 'place-ogmnl'),
            ('CENTRAL SQUARE', 'place-cntsq'),
            ('Harvard Square', 'place-harsq'),
            ('place-portr', 'place-portr'),  # Already an ID
            ('Unknown Station', 'Unknown Station')  # Unknown station
        ]
        
        for station_name, expected_id in test_cases:
            result = self.parser.resolve_station_id(station_name)
            self.assertEqual(result, expected_id)
    
    def test_route_name_resolution(self):
        """Test route name to ID resolution."""
        test_cases = [
            ('Orange Line', 'Orange'),
            ('orange', 'Orange'),
            ('OL', 'Orange'),
            ('Red Line', 'Red'),
            ('Haverhill Line', 'CR-Haverhill'),
            ('haverhill', 'CR-Haverhill'),
            ('Orange', 'Orange'),  # Already an ID
            ('CR-Worcester', 'CR-Worcester'),  # Already an ID
            ('Unknown Route', 'Unknown Route')  # Unknown route
        ]
        
        for route_name, expected_id in test_cases:
            result = self.parser.resolve_route_id(route_name)
            self.assertEqual(result, expected_id)
    
    def test_validation_errors(self):
        """Test configuration validation errors."""
        # Single-station mode without station
        with self.assertRaises(ValueError) as cm:
            config = Config(mode='single-station')
            config.validate()
        self.assertIn("station", str(cm.exception).lower())
        
        # Single-station mode without routes
        with self.assertRaises(ValueError) as cm:
            config = Config(mode='single-station', station='Oak Grove')
            config.validate()
        self.assertIn("routes", str(cm.exception).lower())
        
        # Multi-station mode without route
        with self.assertRaises(ValueError) as cm:
            config = Config(mode='multi-station', from_station='Central')
            config.validate()
        self.assertIn("route", str(cm.exception).lower())
        
        # Invalid mode
        with self.assertRaises(ValueError) as cm:
            config = Config(mode='invalid')
            config.validate()
        self.assertIn("unknown mode", str(cm.exception).lower())
    
    def test_default_values(self):
        """Test default configuration values."""
        config_dict = {
            'mode': 'single-station',
            'station': 'Oak Grove',
            'routes': [
                {'Orange Line': {'inbound': 1}}  # Only inbound specified
            ]
        }
        
        config_path = self.write_config('defaults_test.yaml', config_dict)
        config = self.parser.parse_yaml(config_path)
        
        # Check defaults
        self.assertEqual(config.routes[0].inbound, 1)
        self.assertEqual(config.routes[0].outbound, 0)  # Default when not specified
        self.assertEqual(config.display.time_format, '12h')  # Default time format
        self.assertTrue(config.display.abbreviate)  # Default abbreviation
        self.assertEqual(config.display.refresh, 60)  # Default refresh
    
    def test_load_config_priority(self):
        """Test configuration loading priority."""
        # Create a config file
        config_dict = {'mode': 'single-station', 'station': 'Oak Grove', 'routes': [{'Orange': {'inbound': 1}}]}
        config_path = self.write_config('config.yaml', config_dict)
        
        # Test: explicit config file
        config = self.parser.load_config(config_path=config_path)
        self.assertEqual(config.mode, 'single-station')
        
        # Test: no config file specified should raise error
        with self.assertRaises(ValueError) as cm:
            self.parser.load_config()
        self.assertIn("No configuration found", str(cm.exception))
    
    def test_load_config_default_files(self):
        """Test loading from default config file names."""
        config_dict = {
            'mode': 'single-station',
            'station': 'Oak Grove',
            'routes': [{'Orange Line': {'inbound': 1}}]
        }
        
        # Test each default filename
        for filename in ['config.yaml', 'config.yml', 'instantmbta.yaml']:
            # Create file in current directory
            config_path = Path(filename)
            try:
                with open(config_path, 'w') as f:
                    yaml.dump(config_dict, f)
                
                # Should load without explicit path
                config = self.parser.load_config()
                self.assertEqual(config.mode, 'single-station')
                self.assertEqual(config.station, 'Oak Grove')
            finally:
                # Clean up
                if config_path.exists():
                    config_path.unlink()


if __name__ == '__main__':
    unittest.main()