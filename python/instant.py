import requests
import secret_constants

API_REQUEST = "api_key="+secret_constants.API_KEY

def get_line(line_name):
    r = requests.get('https://api-v3.mbta.com/lines/'+line_name+'?'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)
    print(r.headers)

def get_routes(route_id):
    r = requests.get('https://api-v3.mbta.com/routes/'+route_id+'?'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)
    print(r.headers) 

def get_schedule(route_id):
    r = requests.get('https://api-v3.mbta.com/schedules?filter[route]='+route_id+'&'+API_REQUEST)
    lines_json = r.json()
    print(lines_json)
    print(r.headers)

if __name__ == '__main__':
    #get_line('line-Haverhill')
    get_schedule('CR-Haverhill')
    #get_routes('CR-Haverhill')