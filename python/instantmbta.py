import argparse
import time
from inkytrain import InkyTrain
import logging
import logging.handlers
from infogather import InfoGather

LOG_FILENAME = 'instant.log'

"""
Main class to execute and continuously keep the
Inky e-ink display up-to-date
"""
if __name__ == '__main__':

    logger = logging.getLogger('instantLogger')
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
    it = InkyTrain()
    
    old_stop1_niat = old_stop1_noat = old_stop1_nidt = old_stop1_nodt = old_stop2_nodt = None
    #niat = Next Inbound Arrival Time
    #noat = Next Outbound Arrival Time
    #nidt = Next Inbound Departure Time
    #nodt = Next Outbound Departure Time
    stop1_niat = stop1_noat = stop1_nidt = stop1_nodt = None
    stop2_niat = stop2_noat = stop2_nidt = stop2_nodt = None
    while True:
        try:
            stop1_niat, stop1_noat, stop1_nidt, stop1_nodt = ig.get_current_schedule(route_id, stop1)
            stop2_niat, stop2_noat, stop2_nidt, stop2_nodt = ig.get_current_schedule(route_id, stop2)
            if (old_stop1_niat != stop1_niat or old_stop1_noat != stop1_noat or old_stop2_nodt != stop2_nodt): 
                it.draw_inbound_outbound(route_name, stop1_name, stop2_name, stop1_niat, stop1_noat, stop2_niat, stop2_nodt)
        except Exception as err:
            logger.exception(err)
            continue
        logger.info("{}: {}".format(stop1_name, ' '.join(map(str, [stop1_niat, stop1_noat, stop1_nidt, stop1_nodt]))))
        logger.info("{}: {}".format(stop2_name, ' '.join(map(str, [stop2_niat, stop2_noat, stop2_nidt, stop2_nodt]))))
        old_stop1_niat = stop1_niat
        old_stop1_noat = stop1_noat
        old_stop1_nidt = stop1_nidt
        old_stop1_nodt = stop1_nodt
        old_stop2_nodt = stop2_nodt
        time.sleep(60) #seconds
