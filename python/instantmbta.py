import argparse
import time
import logging
import logging.handlers
import platform
from infogather import InfoGather
import requests
# Conditional import for Raspberry Pi (ARM7l or AARCH64)
if platform.machine() in ('armv7l', 'armv61', 'aarch64'):
    from inkytrain import InkyTrain
else:
    InkyTrain = None

# Configuration Constants
LOG_FILENAME = 'instant.log'
WAIT_TIME_BETWEEN_CHECKS = 120  # seconds
LOG_MAX_BYTES = 2097152  # 2MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT = '%(asctime)s:%(name)s:%(levelname)s: %(message)s'

"""
Main class to execute and continuously keep the
Inky e-ink display up-to-date
"""
def run_display_loop(ig, it, route_id, route_name, stop1, stop1_name, stop2, stop2_name, logger):
    """Main loop to update the display with transit information."""
    old_times = {
        'stop1': {'niat': None, 'noat': None, 'nidt': None, 'nodt': None},
        'stop2': {'nodt': None}
    }
    current_times = {
        'stop1': {'niat': None, 'noat': None, 'nidt': None, 'nodt': None},
        'stop2': {'niat': None, 'noat': None, 'nidt': None, 'nodt': None}
    }
    
    while True:
        try:
            # Get updated schedules
            (current_times['stop1']['niat'], current_times['stop1']['noat'], 
             current_times['stop1']['nidt'], current_times['stop1']['nodt']) = ig.get_current_schedule(route_id, stop1)
            
            (current_times['stop2']['niat'], current_times['stop2']['noat'],
             current_times['stop2']['nidt'], current_times['stop2']['nodt']) = ig.get_current_schedule(route_id, stop2)

            # Check if display needs updating
            if (old_times['stop1']['niat'] != current_times['stop1']['niat'] or
                old_times['stop1']['noat'] != current_times['stop1']['noat'] or
                old_times['stop2']['nodt'] != current_times['stop2']['nodt']):
                if (it is not None):
                    it.draw_inbound_outbound(
                        route_name, stop1_name, stop2_name,
                        current_times['stop1']['nidt'], current_times['stop1']['noat'],
                    current_times['stop2']['niat'], current_times['stop2']['nodt']
                )

        except (requests.exceptions.RequestException, IOError) as err:
            logger.exception(err)
            time.sleep(WAIT_TIME_BETWEEN_CHECKS)
            continue

        # Log current times
        logger.info("%s: %s", stop1_name, ' '.join(map(str, [
            current_times['stop1']['niat'], current_times['stop1']['noat'],
            current_times['stop1']['nidt'], current_times['stop1']['nodt']])))
        logger.info("%s: %s", stop2_name, ' '.join(map(str, [
            current_times['stop2']['niat'], current_times['stop2']['noat'],
            current_times['stop2']['nidt'], current_times['stop2']['nodt']])))

        # Update old times
        old_times['stop1'].update(current_times['stop1'])
        old_times['stop2']['nodt'] = current_times['stop2']['nodt']
        
        time.sleep(WAIT_TIME_BETWEEN_CHECKS)

if __name__ == '__main__':

    logger = logging.getLogger('instantLogger')
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    formatter = logging.Formatter(LOG_FORMAT)
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
    it = InkyTrain() if platform.machine() in ('armv7l', 'armv61', 'aarch64') else None
    
    logger.info(f'System: {platform.machine()}')
    logger.info('Starting InstantMBTA with:')
    logger.info(f'Route: {route_name} ({route_id})')
    logger.info(f'Stop 1: {stop1_name} ({stop1})')
    logger.info(f'Stop 2: {stop2_name} ({stop2})')
    logger.info(f'Display enabled: {it is not None}')
    
    try:
        run_display_loop(ig, it, route_id, route_name, stop1, stop1_name, stop2, stop2_name, logger)
    except KeyboardInterrupt:
        logger.info('Shutting down InstantMBTA')
    except Exception as e:
        logger.exception('Unexpected error occurred:')
        raise