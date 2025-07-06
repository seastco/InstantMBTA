"""Integration test for config parser with real MBTA API."""

import unittest
import tempfile
import yaml
from pathlib import Path

from instantmbta.config_parser import ConfigParser
from instantmbta.infogather import InfoGather


class TestConfigIntegration(unittest.TestCase):
    """Test configuration with real API calls."""
    
    def setUp(self):
        self.parser = ConfigParser()
        self.ig = InfoGather()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def write_config(self, config_dict: dict) -> Path:
        """Helper to write a test config file."""
        config_path = self.temp_path / 'test_config.yaml'
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f)
        return config_path
    
    def test_oak_grove_multi_route(self):
        """Test Oak Grove configuration with Orange Line."""
        config_dict = {
            'mode': 'single-station',
            'station': 'Oak Grove',
            'routes': [
                {'Orange Line': {'inbound': 2}}
            ]
        }
        
        config_path = self.write_config(config_dict)
        config = self.parser.parse_yaml(config_path)
        
        # Verify config parsing
        self.assertEqual(config.station_id, 'place-ogmnl')
        self.assertEqual(config.routes[0].route_id, 'Orange')
        
        # Test with real API
        print("\nTesting Oak Grove Orange Line predictions...")
        
        for route in config.routes:
            if route.has_inbound:
                preds = self.ig.get_predictions_filtered(
                    config.station_id, "0", route.route_id, route.inbound
                )
                print(f"\nRoute: {route.route_name}, Direction: inbound")
                print(f"Found {len(preds)} predictions")
                for i, pred in enumerate(preds):
                    print(f"  Prediction {i+1}: {pred['departure_time']}")
    
    def test_central_square_bidirectional(self):
        """Test Central Square bidirectional configuration."""
        config_dict = {
            'mode': 'single-station',
            'station': 'Central Square',
            'routes': [
                {'Red Line': {'inbound': 2, 'outbound': 2}}
            ]
        }
        
        config_path = self.write_config(config_dict)
        config = self.parser.parse_yaml(config_path)
        
        # Verify config parsing
        self.assertEqual(config.station_id, 'place-cntsq')
        self.assertEqual(config.routes[0].route_id, 'Red')
        
        print("\nTesting Central Square bidirectional predictions...")
        route = config.routes[0]
        
        # Get inbound predictions
        if route.has_inbound:
            inbound = self.ig.get_predictions_filtered(
                config.station_id, "0", route.route_id, route.inbound
            )
            print(f"\nInbound predictions: {len(inbound)}")
            for i, pred in enumerate(inbound):
                print(f"  Inbound {i+1}: {pred['departure_time']}")

        # Get outbound predictions
        if route.has_outbound:
            outbound = self.ig.get_predictions_filtered(
                config.station_id, "1", route.route_id, route.outbound
            )
            print(f"\nOutbound predictions: {len(outbound)}")
            for i, pred in enumerate(outbound):
                print(f"  Outbound {i+1}: {pred['departure_time']}")

    def test_multi_station_mode_schedule(self):
        """Test multi-station mode with schedule data."""
        config_dict = {
            'mode': 'multi-station',
            'route': 'Red Line',
            'from': 'Central Square',
            'to': 'Harvard Square'
        }
        
        config_path = self.write_config(config_dict)
        config = self.parser.parse_yaml(config_path)
        
        print("\nTesting multi-station mode (Central to Harvard)...")
        
        # Get schedule for from station
        from_data = self.ig.get_current_schedule(
            config.route_id, 
            config.from_station_id
        )
        
        print(f"\nFrom {config.from_station}:")
        if from_data[0]:  # Next inbound arrival
            print(f"  Next Inbound Arrival: {from_data[0]}")
        if from_data[2]:  # Next inbound departure
            print(f"  Next Inbound Departure: {from_data[2]}")
        
        # Get schedule for to station  
        to_data = self.ig.get_current_schedule(
            config.route_id,
            config.to_station_id
        )
        
        print(f"\nTo {config.to_station}:")
        if to_data[0]:  # Next inbound arrival
            print(f"  Next Inbound Arrival: {to_data[0]}")


if __name__ == '__main__':
    # Run with verbosity to see print statements
    unittest.main(verbosity=2)