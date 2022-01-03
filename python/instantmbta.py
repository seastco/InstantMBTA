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
    
    old_mh_niat = old_mh_noat = old_mh_nidt = old_mh_nodt = old_ns_nodt = None
    mh_niat = mh_noat = mh_nidt = mh_nodt = None
    ns_niat = ns_noat = ns_nidt = ns_nodt = None
    while True:
        try:
            mh_niat, mh_noat, mh_nidt, mh_nodt = ig.get_current_schedule(route_id, stop1)
            ns_niat, ns_noat, ns_nidt, ns_nodt = ig.get_current_schedule(route_id, stop2)
            if (old_mh_niat != mh_niat or old_mh_noat != mh_noat or old_ns_nodt != ns_nodt): 
                it.draw_inbound_outbound(route_name, stop1_name, stop2_name, mh_niat, mh_noat, ns_niat, ns_nodt)
        except Exception as err:
            logger.exception(err)
            continue
        logger.info("{}: {}".format(stop1_name, ' '.join(map(str, [mh_niat, mh_noat, mh_nidt, mh_nodt]))))
        logger.info("{}: {}".format(stop2_name, ' '.join(map(str, [ns_niat, ns_noat, ns_nidt, ns_nodt]))))
        old_mh_niat = mh_niat
        old_mh_noat = mh_noat
        old_mh_nidt = mh_nidt
        old_mh_nodt = mh_nodt
        old_ns_nodt = ns_nodt
        time.sleep(60) #seconds
