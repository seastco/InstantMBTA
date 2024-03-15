import argparse
import requests
import secret_constants
from datetime import datetime
import time
import logging
import logging.handlers

"""
A collection of functions leveraging the MBTA API (v3)
See: https://www.mbta.com/developers/v3-api
"""

API_REQUEST = "api_key="+secret_constants.API_KEY
API_URL = "https://api-v3.mbta.com"
OUTBOUND = "0"
INBOUND = "1"
LOG_FILENAME = 'instant.log'

class InfoGather():

    def __init__(self):
        self.logger = logging.getLogger('MainLogger')


    """
    Get information for a specific line
    """
    def get_line(self, line_name):
        r = requests.get(API_URL+'/lines/'+line_name+'?'+API_REQUEST)
        return r


    """
    Get information for a specific route
    """
    def get_routes(self, route_id):
        r = requests.get(API_URL+'/routes/'+route_id+'?'+API_REQUEST)
        return r

    """
    Get the scheudle given a route, stop and direction
    """
    def get_schedule(self, route_id, stop_id, direction_id):
        hh_mm = self.get_current_time()
        r = requests.get(API_URL+'/schedules?include=stop,prediction&filter[route]='+\
            route_id+'&filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+
            '&sort=departure_time&filter[min_time]='+hh_mm+'&'+API_REQUEST)
        return r

    """
    Given a STOP ID and a DIRECTION ID (INBOUND or OUTBOUND)
    Returns the predictions
    """
    def get_predictions(self, stop_id, direction_id):
        r = requests.get(API_URL+'/predictions?filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&include=stop&'+API_REQUEST)
        return r

    """
    Given a prediction ID, find the prediction in a list of prediction data
    This is silly because you can't query predictions based on their ID
    even though that's the only thing contained in the schedule/prediction relationship
    """
    def find_prediction_by_id(self, prediction_id, predictions):
        prediction = None
        for prediction in predictions['data']:
            if prediction['id'] == prediction_id:
                return prediction
        self.logger.warn("There should have been a prediction found, but there wasn't.")
        return prediction

    def get_stops(self, route_id):
        r = requests.get(API_URL+'/stops?filter[route]='+route_id+'&'+API_REQUEST)
        return r

    def get_current_time(self):
        current_time = datetime.now().strftime('%H:%M')
        return current_time

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
    def get_current_schedule(self, route_id, stop_id):
        self.logger.info("Getting schedule for {}".format(' '.join(map(str, [route_id, stop_id]))))
        outbound_r = self.get_schedule(route_id, stop_id, OUTBOUND)
        outbound_json = outbound_r.json()
        if len(outbound_json['data']) > 0:
            next_outbound = outbound_json['data'][0] #Sorted by date/time
            next_outbound_arrival_time = next_outbound['attributes']['arrival_time']
            next_outbound_departure_time = next_outbound['attributes']['departure_time']
        else:
            next_outbound = None
            next_outbound_arrival_time = None
            next_outbound_departure_time = None

        inbound_r = self.get_schedule(route_id, stop_id, INBOUND)
        inbound_json = inbound_r.json()
        if len(inbound_json['data']) > 0:
            next_inbound = inbound_json['data'][0] #Sorted by date/time
            next_inbound_arrival_time = next_inbound['attributes']['arrival_time']
            next_inbound_departure_time = next_outbound['attributes']['departure_time']
        else:
            next_inbound = None
            next_inbound_arrival_time = None
            next_inbound_departure_time = None
        try:
            inbound_prediction_data = next_inbound['relationships']['prediction']['data']
        except:
            inbound_prediction_data = None
        if inbound_prediction_data != None:
            inbound_predicted_time_id = inbound_prediction_data['id']
            predictions_inbound = self.get_predictions(stop_id, INBOUND).json()
            inbound_predicted_time_json = self.find_prediction_by_id(inbound_predicted_time_id, predictions_inbound)
            if 'attributes' in inbound_predicted_time_json:
                inbound_predicted_time_arr = inbound_predicted_time_json['attributes']['arrival_time']
                inbound_predicted_time_dep = inbound_predicted_time_json['attributes']['departure_time']
                next_inbound_arrival_time = inbound_predicted_time_arr
                next_inbound_departure_time = inbound_predicted_time_dep
            else:
                self.logger.warn("Unable to find predictions by id for inbound predictions.")
        else:
            self.logger.info("No inbound prediction available for "+stop_id)
        try: 
            outbound_predicted_data = next_outbound['relationships']['prediction']['data']
        except:
            outbound_predicted_data = None
        if outbound_predicted_data != None:
            outbound_predicted_time_id = outbound_predicted_data['id']
            predictions_outbound = self.get_predictions(stop_id, OUTBOUND).json()
            outbound_predicted_time_json = self.find_prediction_by_id(outbound_predicted_time_id, predictions_outbound)
            if 'attributes' in outbound_predicted_time_json:
                outbound_predicted_time_arr = outbound_predicted_time_json['attributes']['arrival_time']
                outbound_predicted_time_dep = outbound_predicted_time_json['attributes']['departure_time']
                next_outbound_arrival_time = outbound_predicted_time_arr
                next_outbound_departure_time = outbound_predicted_time_dep
            else:
                self.logger.warn("Unable to find predictions by id for outbound predictions.")
        else:
            self.logger.info("No outbound prediction available for "+stop_id)

        return next_inbound_arrival_time, next_outbound_arrival_time, next_inbound_departure_time, next_outbound_departure_time

"""Primarily for testing without the inky display"""
if __name__ == '__main__':

    logger = logging.getLogger('MainLogger')
    logger.setLevel(logging.DEBUG)   
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

    old_mh_niat = old_mh_noat = old_mh_nidt = old_mh_nodt = old_ns_nodt = None
    mh_niat = mh_noat = mh_nidt = mh_nodt = None
    ns_niat = ns_noat = ns_nidt = ns_nodt = None

    while True:
        try:
            mh_niat, mh_noat, mh_nidt, mh_nodt = ig.get_current_schedule(route_id, stop1)
            ns_niat, ns_noat, ns_nidt, ns_nodt = ig.get_current_schedule(route_id, stop2)
            if (old_mh_niat != mh_niat or old_mh_noat != mh_noat or old_ns_nodt != ns_nodt):
                logger.debug("Screen refresh activated")
        except Exception as err:
            logger.error("There was an exception with the connection: {0}").format(err)
        logger.info("{}: {}".format(stop1_name, ' '.join(map(str, [mh_niat, mh_noat, mh_nidt, mh_nodt]))))
        logger.info("{}: {}".format(stop2_name, ' '.join(map(str, [ns_niat, ns_noat, ns_nidt, ns_nodt]))))
        old_mh_niat = mh_niat
        old_mh_noat = mh_noat
        old_mh_nidt = mh_nidt
        old_mh_nodt = mh_nodt
        old_ns_nodt = ns_nodt
        time.sleep(60) #seconds
