import unittest
from unittest.mock import patch, MagicMock
import requests
from instantmbta.__main__ import run_display_loop

class TestInstantMBTA(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.ig = MagicMock()
        self.it = MagicMock()
        self.logger = MagicMock()
        self.route_id = "test_route"
        self.route_name = "Test Route"
        self.stop1 = "stop1"
        self.stop1_name = "Stop 1"
        self.stop2 = "stop2"
        self.stop2_name = "Stop 2"

    def test_successful_update(self):
        """Test successful display update."""
        # Mock successful schedule retrieval
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35")   # stop2
        ]

        # Run one iteration of the loop
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [Exception("Break loop")]  # Break after first iteration
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify display was updated
        self.it.draw_inbound_outbound.assert_called_once()
        self.assertEqual(self.ig.get_current_schedule.call_count, 2)

    def test_network_error_handling(self):
        """Test handling of network errors with exponential backoff."""
        # Mock network error followed by success
        self.ig.get_current_schedule.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35")   # stop2
        ]

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify error was logged
        self.logger.error.assert_called()
        
        # Verify exponential backoff was used
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertTrue(sleep_calls[0] < sleep_calls[1])  # Second wait should be longer

    def test_consecutive_failures(self):
        """Test handling of consecutive failures."""
        # Mock continuous network errors
        self.ig.get_current_schedule.side_effect = requests.exceptions.RequestException("Network error")

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, None, None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify error was logged multiple times
        self.assertGreater(self.logger.error.call_count, 1)
        
        # Verify display was not updated
        self.it.draw_inbound_outbound.assert_not_called()

    def test_display_update_conditions(self):
        """Test conditions that trigger display updates."""
        # Mock schedule data
        self.ig.get_current_schedule.side_effect = [
            ("10:00", "11:00", "10:05", "11:05"),  # stop1
            ("10:30", "11:30", "10:35", "11:35"),  # stop2
            ("10:00", "11:00", "10:05", "11:05"),  # stop1 (unchanged)
            ("10:30", "11:30", "10:35", "11:35")   # stop2 (unchanged)
        ]

        # Run with mocked sleep
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Break loop")]
            try:
                run_display_loop(
                    self.ig, self.it,
                    self.route_id, self.route_name,
                    self.stop1, self.stop1_name,
                    self.stop2, self.stop2_name,
                    self.logger
                )
            except Exception:
                pass

        # Verify display was only updated once
        self.assertEqual(self.it.draw_inbound_outbound.call_count, 1)

if __name__ == '__main__':
    unittest.main() 