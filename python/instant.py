import requests
import secret_constants

API_REQUEST = "api_key="+secret_constants.API_KEY
API_URL = "https://api-v3.mbta.com"

print_headers = False

def get_line(line_name):
    r = requests.get(API_URL+'/lines/'+line_name+'?'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)

    if print_headers:
        print(r.headers)

def get_routes(route_id):
    r = requests.get(API_URL+'/routes/'+route_id+'?'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)

    if print_headers:
        print(r.headers)

def get_schedule(route_id, stop_id, direction_id):
    r = requests.get(API_URL+'/schedules?include=stop&filter[route]='+\
        route_id+'&filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)

    if print_headers:
        print(r.headers)

def get_predictions(stop_id, direction_id):
    r = requests.get(API_URL+'/predictions?filter[stop]='+stop_id+'&filter[direction_id]='+direction_id+'&include=stop&'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)

    if print_headers:
        print(r.headers)

def get_stops(route_id):
    r = requests.get(API_URL+'/stops?filter[route]='+route_id+'&'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)

    if print_headers:
        print(r.headers)

if __name__ == '__main__':
    #get_line('line-Haverhill')
    #print("------")
    #get_schedule('CR-Haverhill')
    #print("------")
    #get_routes('CR-Haverhill')
    #get_stops('CR-Haverhill')
    schedule_outbound_mh = get_schedule('CR-Haverhill', 'WR-0075-B', '0')
    #outbound_predictions = get_predictions('WR-0075-B','0')

    #schedule_inbound_mh = get_schedule('CR-Haverhill', 'WR-0075-B', '1')
    #inbound_predictions = get_predictions('WR-0075-B','1')
