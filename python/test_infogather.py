import unittest
from unittest.mock import patch, MagicMock
import requests
from infogather import InfoGather, CircuitBreaker
import time

class TestInfoGather(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.ig = InfoGather()
        # Mock the logger to prevent actual logging during tests
        self.ig.logger = MagicMock()

    def test_verify_connection_success(self):
        """Test successful connection verification."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = self.ig.verify_connection()
            
            self.assertTrue(result)
            self.assertEqual(self.ig.consecutive_failures, 0)
            self.assertIsNotNone(self.ig.last_successful_request)

    def test_verify_connection_failure(self):
        """Test failed connection verification."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")

            result = self.ig.verify_connection()
            
            self.assertFalse(result)
            self.assertEqual(self.ig.consecutive_failures, 1)
            self.assertIsNone(self.ig.last_successful_request)

    def test_make_api_request_with_retries(self):
        """Test API request with retry logic."""
        with patch('requests.get') as mock_get:
            # Simulate two failures followed by success
            mock_get.side_effect = [
                requests.exceptions.RequestException("First failure"),
                requests.exceptions.RequestException("Second failure"),
                MagicMock()
            ]

            # Mock verify_connection to simulate network issues
            with patch.object(self.ig, 'verify_connection') as mock_verify:
                # First two attempts fail, then always succeed
                mock_verify.side_effect = [False, False, True, True, True, True]
                
                # Should succeed on third attempt
                result = self.ig._make_api_request("test_url")
                
                # Verify the number of attempts
                self.assertEqual(mock_get.call_count, 3)
                self.assertGreaterEqual(mock_verify.call_count, 3)
                
                # Verify the result
                self.assertIsNotNone(result)

    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1)
        
        # Simulate a failing function
        def failing_func():
            raise Exception("Test failure")

        # First failure
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.failures, 1)
        self.assertEqual(cb.state, "CLOSED")

        # Second failure should open the circuit
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.failures, 2)
        self.assertEqual(cb.state, "OPEN")

        # Circuit should be open
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.state, "OPEN")

        # Wait for reset timeout
        time.sleep(1.1)
        # Call execute to trigger HALF-OPEN state, but since it fails, state returns to OPEN
        with self.assertRaises(Exception):
            cb.execute(failing_func)
        self.assertEqual(cb.state, "OPEN")
        
        # Now, after timeout, a successful call should close the circuit
        time.sleep(1.1)
        def success_func(*args, **kwargs):
            return "success"
        result = cb.execute(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, "CLOSED")

    def test_exponential_backoff(self):
        """Test exponential backoff in retry logic."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Test error")
            
            with patch.object(self.ig, 'verify_connection', return_value=False):
                with patch('time.sleep') as mock_sleep:
                    try:
                        self.ig._make_api_request("test_url")
                    except Exception:
                        pass
                    
                    # Verify sleep calls with exponential backoff
                    expected_sleeps = [5, 10, 20, 40]  # 5 * 2^n for 4 attempts
                    actual_sleeps = [call[0][0] for call in mock_sleep.call_args_list]
                    self.assertEqual(actual_sleeps, expected_sleeps)

    def test_consecutive_failures_reset(self):
        """Test that consecutive failures counter resets on success."""
        with patch('requests.get') as mock_get:
            # Simulate failure then success
            mock_get.side_effect = [
                requests.exceptions.RequestException("Failure"),
                MagicMock()
            ]
            
            # First attempt fails
            self.ig.verify_connection()
            self.assertEqual(self.ig.consecutive_failures, 1)
            
            # Reset the mock for the second attempt
            mock_get.reset_mock()
            mock_get.return_value = MagicMock()
            
            # Second attempt succeeds
            self.ig.verify_connection()
            self.assertEqual(self.ig.consecutive_failures, 0)

if __name__ == '__main__':
    unittest.main() 