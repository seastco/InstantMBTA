import requests
import secret_constants

API_REQUEST = "api_key="+secret_constants.API_KEY
API_URL = "https://api-v3.mbta.com"

print_headers = False

def get_line(line_name):
    r = requests.get(API_URL+'/lines/'+line_name+'?'+API_REQUEST)
    return r


def get_routes(route_id):
    r = requests.get(API_URL+'/routes/'+route_id+'?'+API_REQUEST)
    return r

def get_schedule(route_id, stop_id, direction_id):
    r = requests.get(API_URL+'/schedules?include=stop&filter[route]='+\
        route_id+'&filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&'+API_REQUEST)
    return r

def get_predictions(stop_id, direction_id):
    r = requests.get(API_URL+'/predictions?filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&include=stop&'+API_REQUEST)
    return r

def get_stops(route_id):
    r = requests.get(API_URL+'/stops?filter[route]='+route_id+'&'+API_REQUEST)
    return r

def get_current_schedule():
    #Start by getting the schedule for a given stop and direction
    #Outbound to Melrose Highlands
    outbound_r = get_schedule('CR-Haverhill', 'place-WR-0075', '1')
    outbound_json = outbound_r.json()
    if len(outbound_json['data']) > 0:
        next_outbound = outbound_json['data'][0] #Sorted by date/time
        next_outbound_arrival_time = next_outbound['attributes']['arrival_time']
        next_outbound_departure_time = next_outbound['attributes']['departure_time']
    else:
        #TODO: Handle empty
        pass

    #Start by getting the schedule for a given stop and direction
    #Outbound to Melrose Highlands
    outbound_pred_r = get_predictions('place-WR-0075', '1')
    outbound_pred_json = outbound_pred_r.json()
    if len(outbound_pred_json['data']) > 0:
        next_outbound_pred = outbound_pred_json['data'][0] #Sorted by date/time
        next_outbound_pred_arrival_time = next_outbound_pred['attributes']['arrival_time']
        next_outbound_pred_departure_time = next_outbound_pred['attributes']['departure_time']
    else:
        #TODO: Handle empty
        pass

    #Inbound to North Station
    inbound_r = get_schedule('CR-Haverhill', 'place-WR-0075', '0')
    inbound_json = inbound_r.json()
    if len(inbound_json['data']) > 0:
        next_inbound = inbound_json['data'][0] #Sorted by date/time
        next_inbound_arrival_time = next_inbound['attributes']['arrival_time']
        next_inbound_departure_time = next_outbound['attributes']['departure_time']
    else:
        #TODO: Handle empty
        pass


    print(next_outbound_arrival_time)
    print(next_inbound_arrival_time)

if __name__ == '__main__':
    #lines_json = r.json()
    #get_line('line-Haverhill')
    #print("------")
    #get_schedule('CR-Haverhill')
    #print("------")
    #get_routes('CR-Haverhill')
    #get_stops('CR-Haverhill')
    #schedule_outbound_mh = get_schedule('CR-Haverhill', 'place-WR-0075', '0')
    #outbound_predictions = get_predictions('place-WR-0075','0')

    #schedule_inbound_mh = get_schedule('CR-Haverhill', 'place-WR-0075', '1')
    #inbound_predictions = get_predictions('place-WR-0075','1')

    get_current_schedule()
