import time
from inkytrain import InkyTrain
from infogather import get_current_schedule
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

    ig = InfoGather()
    it = InkyTrain()
    
    old_mh_niat = old_mh_noat = old_mh_nidt = old_mh_nodt = old_ns_nodt = None
    mh_niat = mh_noat = mh_nidt = mh_nodt = None
    ns_niat = ns_noat = ns_nidt = ns_nodt = None
    route_id = 'CR-Haverhill'
    melrose_highlands = 'place-WR-0075'
    north_station = 'place-north'
    while True:
        try:
            mh_niat, mh_noat, mh_nidt, mh_nodt = get_current_schedule(route_id, melrose_highlands)
            ns_niat, ns_noat, ns_nidt, ns_nodt = get_current_schedule(route_id, north_station)
            if (old_mh_niat != mh_niat or old_mh_noat != mh_noat or old_ns_nodt != ns_nodt): 
                it.draw_inbound_outbound("Haverhill", "Melrose Highlands", "North Station", mh_niat, mh_noat, ns_niat, ns_nodt)
        except Exception as err:
            logger.error("There was an exception with the connection: {0}").format(err)
        logger.info("Melrose Highlands: {}".format(' '.join(map(str, [mh_niat, mh_noat, mh_nidt, mh_nodt]))))
        logger.info("North Station: {}".format(' '.join(map(str, [ns_niat, ns_noat, ns_nidt, ns_nodt]))))
        old_mh_niat = mh_niat
        old_mh_noat = mh_noat
        old_mh_nidt = mh_nidt
        old_mh_nodt = mh_nodt
        old_ns_nodt = ns_nodt
        time.sleep(60) #seconds
