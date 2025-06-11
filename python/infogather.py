"""Module for gathering and processing MBTA transit information using their V3 API."""

import argparse
from datetime import datetime
import time
import logging
import logging.handlers
import requests
import secret_constants

class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, or HALF-OPEN

    def execute(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF-OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            raise e

API_REQUEST = "api_key="+secret_constants.API_KEY
API_URL = "https://api-v3.mbta.com"
"""
"https://api-v3.mbta.com/routes/Orange" 
=>
direction_names":[
"South",
"North"]
South would be inbound at index 0
North would be outbound at index 1
"""
INBOUND = "0"
OUTBOUND = "1"
LOG_FILENAME = 'instant.log'
STANDARD_TIMEOUT = 30
UPDATE_INTERVAL_SECONDS = 60

class InfoGather():
    """
    # A collection of functions leveraging the MBTA API (v3)
    # See: https://www.mbta.com/developers/v3-api
    """

    def __init__(self):
        self.logger = logging.getLogger('instantmbta.infogather')
        self.circuit_breaker = CircuitBreaker()
        self.last_successful_request = None
        self.consecutive_failures = 0
        self.max_retries = 5
        self.base_retry_delay = 5  # seconds

    def verify_connection(self):
        """Verify connection to the MBTA API"""
        try:
            # Simple request to check connectivity
            test_request = API_URL + '/routes?' + API_REQUEST
            response = requests.get(test_request, timeout=STANDARD_TIMEOUT)
            response.raise_for_status()
            self.last_successful_request = time.time()
            self.consecutive_failures = 0
            return True
        except requests.exceptions.RequestException as e:
            self.logger.warning("Connection verification failed: %s", e)
            self.consecutive_failures += 1
            return False

    def _make_api_request(self, request_string):
        """Make an API request with circuit breaker protection and retry logic"""
        def _request():
            return requests.get(request_string, timeout=STANDARD_TIMEOUT)
        
        retry_delay = self.base_retry_delay
        
        for attempt in range(self.max_retries):
            try:
                if not self.verify_connection():
                    if attempt < self.max_retries - 1:
                        self.logger.info("Waiting %d seconds before retry %d/%d", 
                                       retry_delay, attempt + 1, self.max_retries)
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise Exception("Max retries exceeded")
                
                return self.circuit_breaker.execute(_request)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error("Circuit breaker prevented request after %d retries: %s", 
                                    self.max_retries, e)
                    raise
                retry_delay *= 2  # Exponential backoff

    def get_line(self, line_name):
        """
        Get information for a specific line
        """
        request_string = API_URL+'/lines/'+line_name+'?'+API_REQUEST
        self.logger.debug("Getting Line Information %s", request_string)
        return self._make_api_request(request_string)

    def get_routes(self, get_route_id):
        """
        Get information for a specific route
        """
        request_string = API_URL+'/routes/'+get_route_id+'?'+API_REQUEST
        self.logger.debug("Getting Route Information %s", request_string)
        return self._make_api_request(request_string)

    def get_schedule(self, get_route_id, stop_id, direction_id):
        """
        Get the schedule given a route, stop and direction
        """
        hh_mm = self.get_current_time()
        request_string = API_URL+'/schedules?include=stop,prediction&filter[route]='+\
            get_route_id+'&filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&sort=departure_time&filter[min_time]='+hh_mm+'&'+API_REQUEST
        self.logger.debug("Getting schedule %s", request_string)
        return self._make_api_request(request_string)

    def get_predictions(self, stop_id, direction_id):
        """
        Given a STOP ID and a DIRECTION ID (INBOUND or OUTBOUND)
        Returns the predictions
        """
        request_string = API_URL+'/predictions?filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&include=stop&'+API_REQUEST
        self.logger.debug("Getting predictions %s", request_string)
        return self._make_api_request(request_string)

    def find_prediction_by_id(self, prediction_id, predictions):
        """
        Given a prediction ID, find the prediction in a list of prediction data using dictionary lookup.
        
        Args:
            prediction_id (str): The ID of the prediction to find
            predictions (dict): The predictions data from the API
            
        Returns:
            dict: The matching prediction or None if not found
        """
        # Create a dictionary mapping prediction IDs to their data
        prediction_map = {pred['id']: pred for pred in predictions['data']}
        
        # Look up the prediction directly
        prediction = prediction_map.get(prediction_id)
        
        if prediction is None:
            self.logger.error("No prediction found for ID: %s", prediction_id)
        
        return prediction

    def get_stops(self, for_route_id):
        """
        Given a route id, get the stops associated with the route.
        """
        r = requests.get(API_URL+'/stops?filter[route]='+for_route_id+'&'+API_REQUEST, timeout=STANDARD_TIMEOUT)
        return r

    def get_current_time(self):
        """
        Get the current time of the system
        """
        current_time = datetime.now().strftime('%H:%M')
        return current_time

    def get_current_schedule(self, route_id, stop_id):
        """Get current schedule for a route and stop."""
        try:
            current_time = datetime.now().astimezone()
            current_date = current_time.date()
            
            # Get predicted times
            response = self._make_api_request(
                f"{API_URL}/predictions?filter[route]={route_id}&filter[stop]={stop_id}&sort=departure_time&{API_REQUEST}"
            )
            
            if response is None:
                self.logger.error(f"Failed to get predicted times for route {route_id} at stop {stop_id}")
                return None, None, None, None
                
            outbound_predicted_time_json = response.json()
            self.logger.debug(f"Predicted times response: {outbound_predicted_time_json}")
            
            # Get scheduled times
            response = self._make_api_request(
                f"{API_URL}/schedules?filter[route]={route_id}&filter[stop]={stop_id}&sort=departure_time&{API_REQUEST}"
            )
            
            if response is None:
                self.logger.error(f"Failed to get scheduled times for route {route_id} at stop {stop_id}")
                return None, None, None, None
                
            outbound_scheduled_time_json = response.json()
            self.logger.debug(f"Scheduled times response: {outbound_scheduled_time_json}")

            # Process predicted times
            next_inbound_departure_time = None
            next_outbound_departure_time = None
            
            if 'data' in outbound_predicted_time_json:
                for prediction in outbound_predicted_time_json['data']:
                    if 'attributes' in prediction:
                        departure_time = prediction['attributes'].get('departure_time')
                        if departure_time:
                            dt = datetime.fromisoformat(departure_time)
                            if dt > current_time and dt.date() == current_date:
                                if prediction['attributes'].get('direction_id') == 0:  # Inbound
                                    if next_inbound_departure_time is None:
                                        next_inbound_departure_time = departure_time
                                else:  # Outbound
                                    if next_outbound_departure_time is None:
                                        next_outbound_departure_time = departure_time

            # Process scheduled times
            next_inbound_scheduled_time = None
            next_outbound_scheduled_time = None
            
            if 'data' in outbound_scheduled_time_json:
                for schedule in outbound_scheduled_time_json['data']:
                    if 'attributes' in schedule:
                        departure_time = schedule['attributes'].get('departure_time')
                        if departure_time:
                            dt = datetime.fromisoformat(departure_time)
                            if dt > current_time and dt.date() == current_date:
                                if schedule['attributes'].get('direction_id') == 0:  # Inbound
                                    if next_inbound_scheduled_time is None:
                                        next_inbound_scheduled_time = departure_time
                                else:  # Outbound
                                    if next_outbound_scheduled_time is None:
                                        next_outbound_scheduled_time = departure_time

            return (next_inbound_departure_time, next_inbound_scheduled_time,
                    next_outbound_scheduled_time, next_outbound_departure_time)
                    
        except Exception as e:
            self.logger.error(f"Error getting schedule for route {route_id} at stop {stop_id}: {str(e)}")
            return None, None, None, None

if __name__ == '__main__':

    logger = logging.getLogger('MainLogger')
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=2097152, backupCount=5)
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    parser = argparse.ArgumentParser(epilog="For routename, stop1name and stop2name,\
        encapsulate in quotes if name has spaces. (e.g. \"A Place\") \
        See https://www.mbta.com/developers/v3-api for more information \
        on determining the route and stop ID.")
    parser.add_argument("routeid", help="Route ID for which route is being displayed")
    parser.add_argument("routename", help="Human friendly name for route being displayed. If u")
    parser.add_argument("stop1id", help="Stop ID for first stop to display")
    parser.add_argument("stop1name", help="Human friendly name for stop1 being displayed")
    parser.add_argument("stop2id", help="Stop ID for second stop to display")
    parser.add_argument("stop2name", help="Human friendly name for stop2 being displayed")
    parser.add_argument("--once", action="store_true", help="Run the script once instead of continuously")
    args = parser.parse_args()
    route_id = args.routeid
    route_name = args.routename
    stop1 = args.stop1id
    stop1_name = args.stop1name
    stop2 = args.stop2id
    stop2_name = args.stop2name

    ig = InfoGather()

    OLD_MH_NIAT = OLD_MH_NOAT = OLD_MH_NIDT = OLD_MH_NODT = OLD_NS_NODT = None
    MH_NIAT = MH_NOAT = MH_NIDT = MH_NODT = None
    NS_NIAT = NS_NOAT = NS_NIDT = NS_NODT = None

    while True:
        try:
            #NIAT = Next Incoming Arrival Time
            #NOAT = Next Outbound Arrival Time
            #NIDT = Next Inbound Departure Time
            #NODT = Next Outbound Departure Time
            MH_NIAT, MH_NOAT, MH_NIDT, MH_NODT = ig.get_current_schedule(route_id, stop1)
            NS_NIAT, NS_NOAT, NS_NIDT, NS_NODT = ig.get_current_schedule(route_id, stop2)
            if (OLD_MH_NIAT != MH_NIAT or OLD_MH_NOAT != MH_NOAT or OLD_NS_NODT != NS_NODT):
                logger.debug("Screen refresh activated")
        except requests.exceptions.RequestException as err:
            logger.error("There was an exception with the connection: %s", err)
        logger.info("%s - Next Inbound Arrival: %s, Next Outbound Arrival: %s, Next Inbound Departure: %s, Next Outbound Departure: %s", 
                   stop1_name, MH_NIAT, MH_NOAT, MH_NIDT, MH_NODT)
        logger.info("%s - Next Inbound Arrival: %s, Next Outbound Arrival: %s, Next Inbound Departure: %s, Next Outbound Departure: %s", 
                   stop2_name, NS_NIAT, NS_NOAT, NS_NIDT, NS_NODT)
        OLD_MH_NIAT = MH_NIAT
        OLD_MH_NOAT = MH_NOAT
        OLD_MH_NIDT = MH_NIDT
        OLD_MH_NODT = MH_NODT
        OLD_NS_NODT = NS_NODT
        
        if args.once:
            break
            
        time.sleep(UPDATE_INTERVAL_SECONDS) #seconds
