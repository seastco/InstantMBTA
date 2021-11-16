import requests
import secret_constants
from datetime import datetime
import time

API_REQUEST = "api_key="+secret_constants.API_KEY
API_URL = "https://api-v3.mbta.com"
OUTBOUND = "0"
INBOUND = "1"

print_headers = False

def get_line(line_name):
    r = requests.get(API_URL+'/lines/'+line_name+'?'+API_REQUEST)
    return r


def get_routes(route_id):
    r = requests.get(API_URL+'/routes/'+route_id+'?'+API_REQUEST)
    return r

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

def get_current_schedule():
    #Outbound to Melrose Highlands from North Station scheduled
    route_id = 'CR-Haverhill'
    stop_id = 'place-WR-0075'
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

    #Inbound to North Station from Melrose Highlands scheduled
    inbound_r = get_schedule('CR-Haverhill', 'place-WR-0075', INBOUND)
    inbound_json = inbound_r.json()
    if len(inbound_json['data']) > 0:
        next_inbound = inbound_json['data'][0] #Sorted by date/time
        next_inbound_arrival_time = next_inbound['attributes']['arrival_time']
        next_inbound_departure_time = next_outbound['attributes']['departure_time']
    else:
        next_inbound = None
        next_inbound_arrival_time = None
        next_inbound_departure_time = None

    inbound_prediction_data = next_inbound['relationships']['prediction']['data']
    if inbound_prediction_data != None:
        inbound_predicted_time_id = inbound_prediction_data['id']
        inbound_predicted_time_json = get_predictions(stop_id, INBOUND).json()
        outbound_predicted_time_json = find_prediction_by_id(inbound_predicted_time_id, inbound_predicted_time_json)
        inbound_predicted_time_arr = inbound_predicted_time_json['attributes']['arrival_time']
        inbound_predicted_time_dep = inbound_predicted_time_json['attributes']['departure_time']
        next_inbound_arrival_time = inbound_predicted_time_arr
        next_inbound_departure_time = inbound_predicted_time_dep
        print("INBOUND PREDICTION: "+str(inbound_predicted_time_arr))
    else:
        print("No inbound prediction available")
    
    outbound_predicted_data = next_outbound['relationships']['prediction']['data']
    if outbound_predicted_data != None:
        outbound_predicted_time_id = outbound_predicted_data['id']
        outbound_predicted_time_json = get_predictions(stop_id, OUTBOUND).json()
        outbound_predicted_time_json = find_prediction_by_id(outbound_predicted_time_id, outbound_predicted_time_json)
        outbound_predicted_time_arr = outbound_predicted_time_json['attributes']['arrival_time']
        outbound_predicted_time_dep = outbound_predicted_time_json['attributes']['departure_time']
        next_outbound_arrival_time = outbound_predicted_time_arr
        next_outbound_departure_time = outbound_predicted_time_dep
        print("OUTBOUND PREDICTION: "+str(outbound_predicted_time_arr))
    else:
        print("No outbound prediction available")

    return next_inbound_arrival_time, next_outbound_arrival_time, next_inbound_departure_time, next_outbound_departure_time

if __name__ == '__main__':
    while True:
        niat, noat, nidt, nodt = get_current_schedule()
        print(niat)
        print(noat)
        time.sleep(10)
