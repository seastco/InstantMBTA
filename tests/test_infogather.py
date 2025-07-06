import unittest
from unittest.mock import patch, MagicMock
import requests
from instantmbta.infogather import InfoGather, CircuitBreaker
import time
from datetime import datetime, timedelta

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

    def test_get_predictions_filtered_with_pagination(self):
        """Test filtered predictions with pagination handling."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            # Mock response with more predictions than requested
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'id': f'prediction-{i}',
                        'attributes': {
                            'departure_time': f'2025-07-06T10:{15+i}:00-04:00',
                            'arrival_time': f'2025-07-06T10:{14+i}:00-04:00',
                            'direction_id': 0,
                            'departure_uncertainty': 120
                        },
                        'relationships': {
                            'route': {'data': {'id': 'Orange'}},
                            'trip': {'data': {'id': f'trip-{i}'}}
                        }
                    } for i in range(10)  # 10 predictions
                ]
            }
            mock_request.return_value = mock_response
            
            # Request only 3 predictions
            predictions = self.ig.get_predictions_filtered('place-ogmnl', '0', 'Orange', 3)
            
            # Should return only 3
            self.assertEqual(len(predictions), 3)
            self.assertEqual(predictions[0]['id'], 'prediction-0')
            self.assertEqual(predictions[2]['id'], 'prediction-2')

    def test_get_predictions_filtered_missing_times(self):
        """Test handling predictions with missing departure/arrival times."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'id': 'pred-1',
                        'attributes': {
                            'departure_time': '2025-07-06T10:15:00-04:00',
                            'arrival_time': None
                        },
                        'relationships': {'route': {'data': {'id': 'Orange'}}}
                    },
                    {
                        'id': 'pred-2',
                        'attributes': {
                            'departure_time': None,
                            'arrival_time': '2025-07-06T10:20:00-04:00'
                        },
                        'relationships': {'route': {'data': {'id': 'Orange'}}}
                    },
                    {
                        'id': 'pred-3',
                        'attributes': {
                            'departure_time': None,
                            'arrival_time': None  # No times at all
                        },
                        'relationships': {'route': {'data': {'id': 'Orange'}}}
                    },
                    {
                        'id': 'pred-4',
                        'attributes': {
                            'departure_time': '2025-07-06T10:25:00-04:00',
                            'arrival_time': '2025-07-06T10:24:00-04:00'
                        },
                        'relationships': {'route': {'data': {'id': 'Orange'}}}
                    }
                ]
            }
            mock_request.return_value = mock_response
            
            predictions = self.ig.get_predictions_filtered('place-ogmnl', '0')
            
            # Should have 3 predictions (skipping the one with no times)
            self.assertEqual(len(predictions), 3)
            self.assertEqual(predictions[0]['departure_time'], '2025-07-06T10:15:00-04:00')
            self.assertEqual(predictions[1]['departure_time'], '2025-07-06T10:20:00-04:00')
            self.assertEqual(predictions[2]['departure_time'], '2025-07-06T10:25:00-04:00')

    def test_get_predictions_filtered_with_destinations(self):
        """Test extraction of destination information from included trips."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'id': 'pred-1',
                        'attributes': {'departure_time': '2025-07-06T10:15:00-04:00'},
                        'relationships': {
                            'route': {'data': {'id': 'Orange'}},
                            'trip': {'data': {'id': 'trip-forest-hills'}}
                        }
                    },
                    {
                        'id': 'pred-2',
                        'attributes': {'departure_time': '2025-07-06T10:20:00-04:00'},
                        'relationships': {
                            'route': {'data': {'id': 'Orange'}},
                            'trip': {'data': {'id': 'trip-oak-grove'}}
                        }
                    }
                ],
                'included': [
                    {
                        'type': 'trip',
                        'id': 'trip-forest-hills',
                        'attributes': {'headsign': 'Forest Hills'}
                    },
                    {
                        'type': 'trip',
                        'id': 'trip-oak-grove',
                        'attributes': {'headsign': 'Oak Grove'}
                    },
                    {
                        'type': 'stop',
                        'id': 'place-ogmnl',
                        'attributes': {'name': 'Oak Grove'}  # Should ignore non-trip includes
                    }
                ]
            }
            mock_request.return_value = mock_response
            
            predictions = self.ig.get_predictions_filtered('place-ogmnl', '0')
            
            self.assertEqual(len(predictions), 2)
            self.assertEqual(predictions[0]['destination'], 'Forest Hills')
            self.assertEqual(predictions[1]['destination'], 'Oak Grove')

    def test_get_routes_at_stop_various_types(self):
        """Test route retrieval with various route types."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {
                        'id': 'Orange',
                        'attributes': {
                            'long_name': 'Orange Line',
                            'short_name': 'OL',
                            'type': 1,  # Heavy Rail
                            'direction_names': ['Southbound', 'Northbound'],
                            'direction_destinations': ['Forest Hills', 'Oak Grove']
                        }
                    },
                    {
                        'id': '39',
                        'attributes': {
                            'long_name': 'Forest Hills - Back Bay Station',
                            'short_name': '39',
                            'type': 3,  # Bus
                            'direction_names': ['Outbound', 'Inbound'],
                            'direction_destinations': ['Forest Hills', 'Back Bay Station']
                        }
                    },
                    {
                        'id': 'CR-Providence',
                        'attributes': {
                            'long_name': 'Providence/Stoughton Line',
                            'short_name': None,
                            'type': 2,  # Commuter Rail
                            'direction_names': ['Outbound', 'Inbound'],
                            'direction_destinations': ['Providence', 'South Station']
                        }
                    }
                ]
            }
            mock_request.return_value = mock_response
            
            routes = self.ig.get_routes_at_stop('place-forhl')
            
            self.assertEqual(len(routes), 3)
            
            # Check route types
            orange = next(r for r in routes if r['id'] == 'Orange')
            self.assertEqual(orange['type'], 1)
            self.assertEqual(orange['short_name'], 'OL')
            
            bus = next(r for r in routes if r['id'] == '39')
            self.assertEqual(bus['type'], 3)
            self.assertEqual(bus['name'], 'Forest Hills - Back Bay Station')
            
            cr = next(r for r in routes if r['id'] == 'CR-Providence')
            self.assertEqual(cr['type'], 2)
            self.assertIsNone(cr['short_name'])

    def test_api_request_url_construction(self):
        """Test that API URLs are constructed correctly."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            mock_request.return_value = MagicMock(status_code=200, json=lambda: {'data': []})
            
            # Test predictions with all parameters
            self.ig.get_predictions_filtered('place-ogmnl', '0', 'Orange', 5)
            call_url = mock_request.call_args[0][0]
            self.assertIn('filter[stop]=place-ogmnl', call_url)
            self.assertIn('filter[direction_id]=0', call_url)
            self.assertIn('filter[route]=Orange', call_url)
            self.assertIn('page[limit]=10', call_url)  # 5 * 2
            self.assertIn('sort=departure_time', call_url)
            
            # Test predictions without route filter
            mock_request.reset_mock()
            self.ig.get_predictions_filtered('place-cntsq', '1', count=2)
            call_url = mock_request.call_args[0][0]
            self.assertIn('filter[stop]=place-cntsq', call_url)
            self.assertIn('filter[direction_id]=1', call_url)
            self.assertNotIn('filter[route]', call_url)
            self.assertIn('page[limit]=4', call_url)  # 2 * 2

    def test_get_current_schedule_edge_cases(self):
        """Test edge cases in get_current_schedule method."""
        with patch.object(self.ig, '_make_api_request') as mock_request:
            # Mock response with edge cases
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            # Test 1: All times in the past
            current_time = datetime.now().astimezone()
            past_time = current_time - timedelta(hours=1)
            
            mock_response.json.return_value = {
                'data': [
                    {
                        'attributes': {
                            'departure_time': past_time.isoformat(),
                            'arrival_time': past_time.isoformat(),
                            'direction_id': 0
                        }
                    }
                ]
            }
            mock_request.return_value = mock_response
            
            result = self.ig.get_current_schedule('Orange', 'place-ogmnl')
            # Should return None for all values if no future times
            self.assertEqual(result, (None, None, None, None))
            
            # Test 2: Mixed past and future times
            future_time = current_time + timedelta(minutes=10)
            mock_response.json.return_value = {
                'data': [
                    {
                        'attributes': {
                            'departure_time': past_time.isoformat(),
                            'direction_id': 0
                        }
                    },
                    {
                        'attributes': {
                            'departure_time': future_time.isoformat(),
                            'direction_id': 0
                        }
                    }
                ]
            }
            
            result = self.ig.get_current_schedule('Orange', 'place-ogmnl')
            # Should only return future times
            self.assertIsNotNone(result[2])  # inbound departure
            self.assertIn(future_time.strftime('%H:%M'), result[2])

if __name__ == '__main__':
    unittest.main() 