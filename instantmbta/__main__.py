import argparse
import time
import logging
import logging.handlers
import platform
import requests
from pathlib import Path
from .infogather import InfoGather
from .config_parser import ConfigParser
from .display_modes import create_display_mode

PI_PLATFORMS = ("armv7l", "armv6l", "aarch64")

# Conditional import for Raspberry Pi Architectures
if platform.machine() in PI_PLATFORMS:
    from .inkytrain import InkyTrain
    inky_train_cls = InkyTrain
else:
    inky_train_cls = None

# Configuration Constants
LOG_FILENAME = 'instant.log'
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

def run_display_loop(config, display_mode, ig, it, logger):
    """Main loop to update the display with transit information."""
    consecutive_failures = 0
    max_consecutive_failures = 3
    last_display_data = None
    
    while True:
        try:
            # Gather data using the display mode
            logger.debug("Gathering transit data...")
            raw_data = display_mode.gather_data(ig)
            
            # Format for display
            display_data = display_mode.format_for_display(raw_data)
            
            # Reset failure counter on success
            consecutive_failures = 0
            
            # Check if display needs updating (compare with last data)
            should_update = last_display_data is None or display_data != last_display_data
            
            if should_update and it is not None:
                logger.info("Updating display...")
                it.draw_from_display_data(display_data)
                last_display_data = display_data
            
            # Log the current state
            logger.info(f"Display updated for {display_data.title}")
            for line in display_data.lines:
                if line.text.strip():  # Skip empty lines
                    logger.debug(f"  {line.text}")
            
        except (requests.exceptions.RequestException, IOError) as err:
            consecutive_failures += 1
            logger.error("Network error occurred (attempt %d/%d): %s", 
                        consecutive_failures, max_consecutive_failures, err)
            
            # Calculate wait time with exponential backoff
            wait_time = min(config.display.refresh * (2 ** (consecutive_failures - 1)), 300) 
            if consecutive_failures >= max_consecutive_failures:
                logger.error("Maximum consecutive failures reached. Waiting %d seconds before retry.", wait_time)
            
            time.sleep(wait_time)
            continue
            
        except Exception as e:
            logger.exception("Unexpected error in display loop:")
            time.sleep(config.display.refresh)
            continue
        
        # Wait before next update
        time.sleep(config.display.refresh)

def run_once(config, display_mode, ig, it, logger):
    """Run the display update once (for testing)."""
    try:
        # Gather data
        logger.info("Gathering transit data...")
        raw_data = display_mode.gather_data(ig)
        
        # Format for display
        display_data = display_mode.format_for_display(raw_data)
        
        # Update display if available
        if it is not None:
            logger.info("Updating display...")
            it.draw_from_display_data(display_data)
        
        # Log the results
        logger.info(f"Display data for {display_data.title}:")
        for line in display_data.lines:
            if line.text.strip():
                logger.info(f"  {line.text}")
                
    except Exception as e:
        logger.exception("Error during single run:")
        raise

def main():
    """Main entry point for InstantMBTA."""
    parser = argparse.ArgumentParser(
        description="Real-time MBTA transit display for Raspberry Pi Inky pHAT"
    )
    
    # Config-based arguments
    parser.add_argument("--config", type=Path, help="Path to YAML configuration file")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuously")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                       help="Set the logging level")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = setup_logging(log_to_console=args.once, log_level=log_level)
    
    # Load configuration
    config_parser = ConfigParser()
    try:
        config = config_parser.load_config(config_path=args.config)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        parser.print_help()
        return 1
    
    # Create components
    ig = InfoGather()
    it = inky_train_cls() if inky_train_cls is not None else None
    display_mode = create_display_mode(config)
    
    # Log startup info
    logger.info('System: %s', platform.machine())
    logger.info('Starting InstantMBTA')
    logger.info('Mode: %s', config.mode)
    logger.info('Display enabled: %s', it is not None)
    
    if config.mode == 'single-station':
        logger.info('Station: %s (%s)', config.station, config.station_id)
        logger.info('Tracking %d route(s)', len(config.routes))
    else:
        logger.info('Route: %s (%s)', config.route_name, config.route_id)
        logger.info('From: %s (%s)', config.from_station, config.from_station_id)
        logger.info('To: %s (%s)', config.to_station, config.to_station_id)
    
    try:
        if args.once:
            run_once(config, display_mode, ig, it, logger)
        else:
            run_display_loop(config, display_mode, ig, it, logger)
    except KeyboardInterrupt:
        logger.info('Shutting down InstantMBTA')
    except Exception as e:
        logger.exception('Unexpected error occurred:')
        raise

if __name__ == '__main__':
    main()