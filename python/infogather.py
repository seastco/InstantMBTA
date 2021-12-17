import requests
import secret_constants
from datetime import datetime
import time

"""
A collection of functions leveraging the MBTA API (v3)
See: https://www.mbta.com/developers/v3-api
"""

API_REQUEST = "api_key="+secret_constants.API_KEY
API_URL = "https://api-v3.mbta.com"
OUTBOUND = "0"
INBOUND = "1"

print_headers = False

"""
Get information for a specific line
"""
def get_line(line_name):
    r = requests.get(API_URL+'/lines/'+line_name+'?'+API_REQUEST)
    return r


"""
Get information for a specific route
"""
def get_routes(route_id):
    r = requests.get(API_URL+'/routes/'+route_id+'?'+API_REQUEST)
    return r

"""
Get the scheudle given a route, stop and direction
"""
def get_schedule(route_id, stop_id, direction_id):
    hh_mm = get_current_time()
    r = requests.get(API_URL+'/schedules?include=stop,prediction&filter[route]='+\
        route_id+'&filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+
        '&sort=arrival_time&filter[min_time]='+hh_mm+'&'+API_REQUEST)

    return r

"""
Given a STOP ID and a DIRECTION ID (INBOUND or OUTBOUND)
Returns the predictions
"""
def get_predictions(stop_id, direction_id):
    r = requests.get(API_URL+'/predictions?filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&include=stop&'+API_REQUEST)
    return r

"""
Given a prediction ID, find the prediction in a list of prediction data
This is silly because you can't query predictions based on their ID
even though that's the only thing contained in the schedule/prediction relationship
"""
def find_prediction_by_id(prediction_id, predictions):
    prediction = None
    for prediction in predictions['data']:
        if prediction['id'] == prediction_id:
            return prediction
    print("There should have been a prediction found, but there wasn't.")
    return prediction

def get_stops(route_id):
    r = requests.get(API_URL+'/stops?filter[route]='+route_id+'&'+API_REQUEST)
    return r

def get_current_time():
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
"""
def get_current_schedule(route_id, stop_id):
    outbound_r = get_schedule(route_id, stop_id, OUTBOUND)
    outbound_json = outbound_r.json()
    if len(outbound_json['data']) > 0:
        next_outbound = outbound_json['data'][0] #Sorted by date/time
        next_outbound_arrival_time = next_outbound['attributes']['arrival_time']
        next_outbound_departure_time = next_outbound['attributes']['departure_time']
    else:
        next_outbound = None
        next_outbound_arrival_time = None
        next_outbound_departure_time = None

    inbound_r = get_schedule(route_id, stop_id, INBOUND)
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
        predictions_inbound = get_predictions(stop_id, INBOUND).json()
        inbound_predicted_time_json = find_prediction_by_id(inbound_predicted_time_id, predictions_inbound)
        if 'attributes' in inbound_predicted_time_json:
            inbound_predicted_time_arr = inbound_predicted_time_json['attributes']['arrival_time']
            inbound_predicted_time_dep = inbound_predicted_time_json['attributes']['departure_time']
            next_inbound_arrival_time = inbound_predicted_time_arr
            next_inbound_departure_time = inbound_predicted_time_dep
        else:
            print("Unable to find predictions by id for inbound predictions.")
    else:
        print("No inbound prediction available for "+stop_id)
    try: 
        outbound_predicted_data = next_outbound['relationships']['prediction']['data']
    except:
        outbound_predicted_data = None
    if outbound_predicted_data != None:
        outbound_predicted_time_id = outbound_predicted_data['id']
        predictions_outbound = get_predictions(stop_id, OUTBOUND).json()
        outbound_predicted_time_json = find_prediction_by_id(outbound_predicted_time_id, predictions_outbound)
        if 'attributes' in outbound_predicted_time_json:
            outbound_predicted_time_arr = outbound_predicted_time_json['attributes']['arrival_time']
            outbound_predicted_time_dep = outbound_predicted_time_json['attributes']['departure_time']
            next_outbound_arrival_time = outbound_predicted_time_arr
            next_outbound_departure_time = outbound_predicted_time_dep
        else:
            print("Unable to find predictions by id for outbound predictions.")
    else:
        print("No outbound prediction available for "+stop_id)

    return next_inbound_arrival_time, next_outbound_arrival_time, next_inbound_departure_time, next_outbound_departure_time

"""Primarily for testing without the inky display"""
if __name__ == '__main__':
    old_mh_niat = None
    old_mh_noat = None
    old_mh_nidt = None
    old_mh_nodt = None
    old_ns_nodt = None
    route_id = 'CR-Haverhill'
    melrose_highlands = 'place-WR-0075'
    north_station = 'place-north'
    while True:
        mh_niat, mh_noat, mh_nidt, mh_nodt = get_current_schedule(route_id, melrose_highlands)
        ns_niat, ns_noat, ns_nidt, ns_nodt = get_current_schedule(route_id, north_station)
        if (old_mh_niat != mh_niat or old_mh_noat != mh_noat or old_ns_nodt != ns_nodt):
            print("Screen refresh activated")
        print(mh_niat, mh_noat, mh_nidt, mh_nodt)
        print(ns_niat, ns_noat, ns_nidt, ns_nodt)
        print("-----")
        old_mh_niat = mh_niat
        old_mh_noat = mh_noat
        old_mh_nidt = mh_nidt
        old_mh_nodt = mh_nodt
        old_ns_nodt = ns_nodt
        time.sleep(60) #seconds
