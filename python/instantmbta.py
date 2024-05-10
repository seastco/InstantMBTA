import argparse
import time
import logging
import logging.handlers
from inkytrain import InkyTrain
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

    OLD_STOP1_NIAT = OLD_STOP1_NOAT = OLD_STOP1_NIDT = OLD_STOP1_NODT = OLD_STOP2_NODT = None
    #niat = Next Inbound Arrival Time
    #noat = Next Outbound Arrival Time
    #nidt = Next Inbound Departure Time
    #nodt = Next Outbound Departure Time
    STOP1_NIAT = STOP1_NOAT = STOP1_NIDT = STOP1_NODT = None
    STOP2_NIAT = STOP2_NOAT = STOP2_NIDT = STOP2_NODT = None
    while True:
        try:
            STOP1_NIAT, STOP1_NOAT, STOP1_NIDT, STOP1_NODT = ig.get_current_schedule(route_id, stop1)
            STOP2_NIAT, STOP2_NOAT, STOP2_NIDT, STOP2_NODT = ig.get_current_schedule(route_id, stop2)
            if (OLD_STOP1_NIAT != STOP1_NIAT or OLD_STOP1_NOAT != STOP1_NOAT or OLD_STOP2_NODT != STOP2_NODT):
                it.draw_inbound_outbound(route_name, stop1_name, stop2_name, STOP1_NIAT, STOP1_NOAT, STOP2_NIAT, STOP2_NODT)
        except Exception as err:
            logger.exception(err)
            continue
        logger.info("{}: {}".format(stop1_name, ' '.join(map(str, [STOP1_NIAT, STOP1_NOAT, STOP1_NIDT, STOP1_NODT]))))
        logger.info("{}: {}".format(stop2_name, ' '.join(map(str, [STOP2_NIAT, STOP2_NOAT, STOP2_NIDT, STOP2_NODT]))))
        OLD_STOP1_NIAT = STOP1_NIAT
        OLD_STOP1_NOAT = STOP1_NOAT
        OLD_STOP1_NIDT = STOP1_NIDT
        OLD_STOP1_NODT = STOP1_NODT
        OLD_STOP2_NODT = STOP2_NODT
        time.sleep(120) #seconds
