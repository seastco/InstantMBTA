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

    def _make_api_request(self, request_string):
        """Make an API request with circuit breaker protection"""
        def _request():
            return requests.get(request_string, timeout=STANDARD_TIMEOUT)
        
        try:
            return self.circuit_breaker.execute(_request)
        except Exception as e:
            self.logger.error("Circuit breaker prevented request: %s", e)
            raise

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

    def get_current_schedule(self, a_route_id, stop_id):
        """
        Get the current schedule given a route id and stop id
        It will first get the schedule and then see if there are any predictions.
        If there are predictions for the route and stop it will choose the prediction over
        the original schedule.
        If there is neither a scheduled time in the same day nor a prediction,
        it will return None for that specific entry

        The closest time is that which is used.
        route_id: The ID of the route
        stop_id: The ID of the stop

        Returns
        next_inbound_arrival_time, 
        next_outbound_arrival_time, 
        next_inbound_departure_time, 
        next_outbound_departure_time
        """
        self.logger.info("Getting schedule for %s", ' '.join(map(str, [a_route_id, stop_id])))
        outbound_r = self.get_schedule(a_route_id, stop_id, OUTBOUND)
        outbound_json = outbound_r.json()
        outbound_predicted_data = None  # Initialize here
        if len(outbound_json['data']) > 0:
            next_outbound = outbound_json['data'][0] #Sorted by date/time
            next_outbound_arrival_time = next_outbound['attributes']['arrival_time']
            next_outbound_departure_time = next_outbound['attributes']['departure_time']
        else:
            next_outbound = None
            next_outbound_arrival_time = None
            next_outbound_departure_time = None
        inbound_r = self.get_schedule(a_route_id, stop_id, INBOUND)
        inbound_json = inbound_r.json()
        inbound_prediction_data = None  # Initialize here
        if len(inbound_json['data']) > 0:
            next_inbound = inbound_json['data'][0] #Sorted by date/time
            next_inbound_arrival_time = next_inbound['attributes']['arrival_time']
            next_inbound_departure_time = next_inbound['attributes']['departure_time']
        else:
            next_inbound = None
            next_inbound_arrival_time = None
            next_inbound_departure_time = None
        if next_inbound is not None:
            try:
                inbound_prediction_data = next_inbound['relationships']['prediction']['data']
            except KeyError:
                inbound_prediction_data = None
        if inbound_prediction_data is not None:
            inbound_predicted_time_id = inbound_prediction_data['id']
            predictions_inbound = self.get_predictions(stop_id, INBOUND).json()
            inbound_predicted_time_json = self.find_prediction_by_id(inbound_predicted_time_id, predictions_inbound)
            if 'attributes' in inbound_predicted_time_json:
                inbound_predicted_time_arr = inbound_predicted_time_json['attributes']['arrival_time']
                inbound_predicted_time_dep = inbound_predicted_time_json['attributes']['departure_time']
                next_inbound_arrival_time = inbound_predicted_time_arr
                next_inbound_departure_time = inbound_predicted_time_dep
            else:
                self.logger.error("Unable to find predictions by id for inbound predictions.")
        else:
            self.logger.info("No inbound prediction available for %s", stop_id)
        if next_outbound is not None:
            try:
                outbound_predicted_data = next_outbound['relationships']['prediction']['data']
            except KeyError:
                outbound_predicted_data = None
        if outbound_predicted_data is not None:
            outbound_predicted_time_id = outbound_predicted_data['id']
            predictions_outbound = self.get_predictions(stop_id, OUTBOUND).json()
            outbound_predicted_time_json = self.find_prediction_by_id(outbound_predicted_time_id, predictions_outbound)
            if 'attributes' in outbound_predicted_time_json:
                outbound_predicted_time_arr = outbound_predicted_time_json['attributes']['arrival_time']
                outbound_predicted_time_dep = outbound_predicted_time_json['attributes']['departure_time']
                next_outbound_arrival_time = outbound_predicted_time_arr
                next_outbound_departure_time = outbound_predicted_time_dep
            else:
                self.logger.error("Unable to find predictions by id for outbound predictions.")
        else:
            self.logger.info("No outbound prediction available for %s", stop_id)

        return next_inbound_arrival_time, next_outbound_arrival_time, next_inbound_departure_time, next_outbound_departure_time

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
        logger.info("%s: %s", stop1_name, ' '.join(map(str, [MH_NIAT, MH_NOAT, MH_NIDT, MH_NODT])))
        logger.info("%s: %s", stop2_name, ' '.join(map(str, [NS_NIAT, NS_NOAT, NS_NIDT, NS_NODT])))
        OLD_MH_NIAT = MH_NIAT
        OLD_MH_NOAT = MH_NOAT
        OLD_MH_NIDT = MH_NIDT
        OLD_MH_NODT = MH_NODT
        OLD_NS_NODT = NS_NODT
        time.sleep(UPDATE_INTERVAL_SECONDS) #seconds
