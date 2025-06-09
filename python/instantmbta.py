import argparse
import time
import logging
import logging.handlers
import platform
from infogather import InfoGather
import requests

PI_PLATFORMS = ("armv7l", "armv6l", "aarch64")

# Conditional import for Raspberry Pi Architectures
if platform.machine() in PI_PLATFORMS:
    from inkytrain import InkyTrain
    inky_train_cls = InkyTrain
else:
    inky_train_cls = None

# Configuration Constants
LOG_FILENAME = 'instant.log'
WAIT_TIME_BETWEEN_CHECKS = 120  # seconds
LOG_MAX_BYTES = 2097152  # 2MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT = '%(asctime)s:%(name)s:%(levelname)s: %(message)s'

def setup_logging(log_to_console=True, log_level=logging.INFO):
    """Set up and return the main logger for InstantMBTA with the specified output and log level."""
    main_logger = logging.getLogger("instantmbta")
    main_logger.setLevel(log_level)
    formatter = logging.Formatter(LOG_FORMAT)
    if log_to_console:
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    handler.setFormatter(formatter)
    main_logger.handlers.clear()  # Avoid duplicate logs
    main_logger.addHandler(handler)
    return main_logger

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
    
    consecutive_failures = 0
    max_consecutive_failures = 3
    base_wait_time = WAIT_TIME_BETWEEN_CHECKS
    
    while True:
        try:
            # Get updated schedules
            (current_times['stop1']['niat'], current_times['stop1']['noat'], 
             current_times['stop1']['nidt'], current_times['stop1']['nodt']) = ig.get_current_schedule(route_id, stop1)
            
            (current_times['stop2']['niat'], current_times['stop2']['noat'],
             current_times['stop2']['nidt'], current_times['stop2']['nodt']) = ig.get_current_schedule(route_id, stop2)

            # Reset failure counter on success
            consecutive_failures = 0

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
            consecutive_failures += 1
            logger.error("Network error occurred (attempt %d/%d): %s", 
                           consecutive_failures, max_consecutive_failures, err)
            
            # Calculate wait time with exponential backoff
            wait_time = min(base_wait_time * (2 ** (consecutive_failures - 1)), 300)  # Cap at 5 minutes
            
            if consecutive_failures >= max_consecutive_failures:
                logger.error("Maximum consecutive failures reached. Waiting %d seconds before retry.", wait_time)
            
            time.sleep(wait_time)
            continue

        # Log current times
        logger.info("%s - Next Inbound Arrival: %s, Next Outbound Arrival: %s, Next Inbound Departure: %s, Next Outbound Departure: %s", 
                   stop1_name, current_times['stop1']['niat'], current_times['stop1']['noat'], current_times['stop1']['nidt'], current_times['stop1']['nodt'])
        logger.info("%s - Next Inbound Arrival: %s, Next Outbound Arrival: %s, Next Inbound Departure: %s, Next Outbound Departure: %s", 
                   stop2_name, current_times['stop2']['niat'], current_times['stop2']['noat'], current_times['stop2']['nidt'], current_times['stop2']['nodt'])

        # Update old times
        old_times['stop1'].update(current_times['stop1'])
        old_times['stop2']['nodt'] = current_times['stop2']['nodt']
        
        time.sleep(WAIT_TIME_BETWEEN_CHECKS)

if __name__ == '__main__':

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
    parser.add_argument("--once", action="store_true", help="Run once instead of continuously")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level")
    args = parser.parse_args()
    route_id = args.routeid
    route_name = args.routename
    stop1 = args.stop1id
    stop1_name = args.stop1name
    stop2 = args.stop2id
    stop2_name = args.stop2name

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = setup_logging(log_to_console=args.once, log_level=log_level)

    ig = InfoGather()
    it = inky_train_cls() if inky_train_cls is not None else None
    
    logger.info('System: %s', platform.machine())
    logger.info('Starting InstantMBTA with:')
    logger.info('Route: %s (%s)', route_name, route_id)
    logger.info('Stop 1: %s (%s)', stop1_name, stop1)
    logger.info('Stop 2: %s (%s)', stop2_name, stop2)
    logger.info('Display enabled: %s', it is not None)
    
    try:
        if args.once:
            # Run once
            STOP1_NIAT, STOP1_NOAT, STOP1_NIDT, STOP1_NODT = ig.get_current_schedule(route_id, stop1)
            STOP2_NIAT, STOP2_NOAT, STOP2_NIDT, STOP2_NODT = ig.get_current_schedule(route_id, stop2)
            if it is not None:
                it.draw_inbound_outbound(
                    route_name, stop1_name, stop2_name,
                    STOP1_NIDT, STOP1_NOAT, STOP2_NIAT, STOP2_NODT
                )
            logger.info("%s - Next Inbound Arrival: %s, Next Outbound Arrival: %s, Next Inbound Departure: %s, Next Outbound Departure: %s", 
                       stop1_name, STOP1_NIAT, STOP1_NOAT, STOP1_NIDT, STOP1_NODT)
            logger.info("%s - Next Inbound Arrival: %s, Next Outbound Arrival: %s, Next Inbound Departure: %s, Next Outbound Departure: %s", 
                       stop2_name, STOP2_NIAT, STOP2_NOAT, STOP2_NIDT, STOP2_NODT)
        else:
            # Run continuously
            run_display_loop(ig, it, route_id, route_name, stop1, stop1_name, stop2, stop2_name, logger)
    except KeyboardInterrupt:
        logger.info('Shutting down InstantMBTA')
    except Exception as e:
        logger.exception('Unexpected error occurred:')
        raise