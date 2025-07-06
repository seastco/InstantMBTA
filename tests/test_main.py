"""Tests for the main module."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import yaml
import logging
import requests
from instantmbta.__main__ import run_display_loop, run_once, main
from instantmbta.config_parser import Config, DisplayConfig
from instantmbta.display_modes import DisplayData, DisplayLine


class TestMainModule(unittest.TestCase):
    """Test the config-driven main module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(
            mode='single-station',
            station='Oak Grove',
            station_id='place-ogmnl',
            display=DisplayConfig(refresh=60)
        )
        self.display_mode = Mock()
        self.ig = Mock()
        self.it = Mock()
        self.logger = Mock()
    
    def test_run_once_success(self):
        """Test successful single run."""
        # Mock display data
        display_data = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[
                DisplayLine("OL In: 10:15 AM", is_route=True),
                DisplayLine("OL In: 10:23 AM", indent=True)
            ]
        )
        
        self.display_mode.gather_data.return_value = {'predictions': []}
        self.display_mode.format_for_display.return_value = display_data
        
        # Run once
        run_once(self.config, self.display_mode, self.ig, self.it, self.logger)
        
        # Verify calls
        self.display_mode.gather_data.assert_called_once_with(self.ig)
        self.display_mode.format_for_display.assert_called_once()
        self.it.draw_from_display_data.assert_called_once_with(display_data)
        
        # Verify logging
        self.logger.info.assert_called()
    
    def test_run_once_error_handling(self):
        """Test error handling in single run."""
        self.display_mode.gather_data.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            run_once(self.config, self.display_mode, self.ig, self.it, self.logger)
        
        self.logger.exception.assert_called()
    
    def test_run_display_loop_update_detection(self):
        """Test display update detection in continuous loop."""
        # Create two different display data objects
        display_data1 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:15 AM")]
        )
        
        display_data2 = DisplayData(
            title="Oak Grove", 
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:23 AM")]  # Different time
        )
        
        # Mock to return different data each time
        self.display_mode.gather_data.return_value = {}
        self.display_mode.format_for_display.side_effect = [
            display_data1, display_data2
        ]
        
        # Run loop with mocked sleep to break after 2 iterations
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt()]
            
            with self.assertRaises(KeyboardInterrupt):
                run_display_loop(
                    self.config, self.display_mode, 
                    self.ig, self.it, self.logger
                )
        
        # Should update display both times (first time and when data changes)
        self.assertEqual(self.it.draw_from_display_data.call_count, 2)
    
    def test_run_display_loop_network_error_recovery(self):
        """Test network error handling with exponential backoff."""
        # Simulate network error then success
        display_data = DisplayData(title="Oak Grove", date="07/06/25")
        
        self.display_mode.gather_data.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            {}  # Success
        ]
        self.display_mode.format_for_display.return_value = display_data
        
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None, KeyboardInterrupt()]
            
            with self.assertRaises(KeyboardInterrupt):
                run_display_loop(
                    self.config, self.display_mode,
                    self.ig, self.it, self.logger
                )
        
        # Verify exponential backoff
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls[0], 60)   # First failure: 1x refresh
        self.assertEqual(sleep_calls[1], 120)  # Second failure: 2x refresh
        
        # Verify error logging
        self.assertEqual(self.logger.error.call_count, 2)
    
    def test_main_with_config_file(self):
        """Test main function with config file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test config
            config_path = Path(tmp_dir) / 'test.yaml'
            with open(config_path, 'w') as f:
                yaml.dump({
                    'mode': 'single-station',
                    'station': 'Oak Grove',
                    'routes': [{'Orange Line': {'inbound': 2}}]
                }, f)
            
            # Mock command line args
            test_args = ['instantmbta', '--config', str(config_path), '--once']
            
            with patch('sys.argv', test_args):
                with patch('instantmbta.__main__.InfoGather'):
                    with patch('instantmbta.__main__.create_display_mode'):
                        with patch('instantmbta.__main__.run_once') as mock_run:
                            # Mock platform check to avoid display import
                            with patch('platform.machine', return_value='x86_64'):
                                main()
            
            mock_run.assert_called_once()
    
    def test_main_error_handling(self):
        """Test main function error handling."""
        test_args = ['instantmbta']  # No config
        
        with patch('sys.argv', test_args):
            with patch('platform.machine', return_value='x86_64'):
                result = main()
        
        self.assertEqual(result, 1)  # Should return error code
    
    def test_display_update_optimization(self):
        """Test that display only updates when data changes."""
        # Create identical display data objects
        display_data1 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:15 AM")]
        )
        
        display_data2 = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:15 AM")]
        )
        
        # Mock to return same data twice, then different data
        self.display_mode.gather_data.return_value = {}
        self.display_mode.format_for_display.side_effect = [
            display_data1, display_data2, 
            DisplayData(title="Oak Grove", date="07/06/25", lines=[DisplayLine("OL In: 10:23 AM")])
        ]
        
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None, KeyboardInterrupt()]
            
            with self.assertRaises(KeyboardInterrupt):
                run_display_loop(self.config, self.display_mode, self.ig, self.it, self.logger)
        
        # Display should update only twice (initial + when data changes)
        self.assertEqual(self.it.draw_from_display_data.call_count, 2)

    def test_run_display_loop_unexpected_error_recovery(self):
        """Test recovery from unexpected errors in display loop."""
        # Simulate various unexpected errors
        self.display_mode.gather_data.side_effect = [
            RuntimeError("Unexpected error"),
            {},  # Success after error
            KeyboardInterrupt()
        ]
        
        self.display_mode.format_for_display.return_value = DisplayData(
            title="Test", date="07/06/25"
        )
        
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None]
            
            with self.assertRaises(KeyboardInterrupt):
                run_display_loop(
                    self.config, self.display_mode, 
                    self.ig, self.it, self.logger
                )
        
        # Should log exception but continue
        self.logger.exception.assert_called_once()
        # Should eventually update display after recovery
        self.it.draw_from_display_data.assert_called()

    def test_run_once_no_display_hardware(self):
        """Test run_once when no display hardware is available."""
        # Simulate no display (it = None)
        display_data = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[
                DisplayLine("OL In: 10:15 AM"),
                DisplayLine("CR In: 10:30 AM")
            ]
        )
        
        self.display_mode.gather_data.return_value = {}
        self.display_mode.format_for_display.return_value = display_data
        
        # Run with no display
        run_once(self.config, self.display_mode, self.ig, None, self.logger)
        
        # Should not crash, should log results
        self.logger.info.assert_called()
        log_calls = [call[0][0] for call in self.logger.info.call_args_list]
        self.assertTrue(any("OL In: 10:15 AM" in call for call in log_calls))

    def test_main_config_file_not_found(self):
        """Test main function when config file doesn't exist."""
        test_args = ['instantmbta', '--config', '/nonexistent/config.yaml', '--once']
        
        with patch('sys.argv', test_args):
            with patch('platform.machine', return_value='x86_64'):
                result = main()
        
        self.assertEqual(result, 1)

    def test_main_keyboard_interrupt_handling(self):
        """Test graceful shutdown on Ctrl+C."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / 'test.yaml'
            with open(config_path, 'w') as f:
                yaml.dump({
                    'mode': 'single-station',
                    'station': 'Oak Grove',
                    'routes': [{'Orange Line': {'inbound': 2}}]
                }, f)
            
            test_args = ['instantmbta', '--config', str(config_path)]
            
            with patch('sys.argv', test_args):
                with patch('instantmbta.__main__.InfoGather'):
                    with patch('instantmbta.__main__.create_display_mode'):
                        with patch('instantmbta.__main__.run_display_loop') as mock_loop:
                            mock_loop.side_effect = KeyboardInterrupt()
                            with patch('platform.machine', return_value='x86_64'):
                                # Should not raise, should handle gracefully
                                main()
            
            # Should log shutdown message
            mock_loop.assert_called_once()

    def test_display_data_changes_detection(self):
        """Test various scenarios of display data change detection."""
        # Test different types of changes
        base_data = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[DisplayLine("OL In: 10:15 AM")],
            refresh_seconds=60
        )
        
        changes = [
            # Different title
            DisplayData(title="Wellington", date="07/06/25", lines=[DisplayLine("OL In: 10:15 AM")]),
            # Different date
            DisplayData(title="Oak Grove", date="07/07/25", lines=[DisplayLine("OL In: 10:15 AM")]),
            # Different lines
            DisplayData(title="Oak Grove", date="07/06/25", lines=[DisplayLine("OL In: 10:23 AM")]),
            # Additional line
            DisplayData(title="Oak Grove", date="07/06/25", lines=[
                DisplayLine("OL In: 10:15 AM"),
                DisplayLine("OL In: 10:23 AM")
            ]),
            # Different refresh
            DisplayData(title="Oak Grove", date="07/06/25", lines=[DisplayLine("OL In: 10:15 AM")], refresh_seconds=30),
        ]
        
        for changed_data in changes:
            # All should be detected as different
            should_update = base_data != changed_data
            self.assertTrue(should_update, f"Failed to detect change: {changed_data}")

    def test_empty_predictions_handling(self):
        """Test handling of empty predictions gracefully."""
        # Create display data with no predictions
        empty_display = DisplayData(
            title="Oak Grove",
            date="07/06/25",
            lines=[],  # No predictions
            refresh_seconds=60
        )
        
        self.display_mode.gather_data.return_value = {'predictions': [], 'errors': []}
        self.display_mode.format_for_display.return_value = empty_display
        
        # Should not crash
        run_once(self.config, self.display_mode, self.ig, self.it, self.logger)
        
        # Display should still be called with empty data
        self.it.draw_from_display_data.assert_called_once_with(empty_display)


if __name__ == '__main__':
    unittest.main()