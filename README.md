# InstantMBTA

InstantMBTA is a service for getting the latest MBTA schedules and alerts and displaying them on a Raspberry Pi [Inky pHAT](https://github.com/pimoroni/inky).

This project retrieves the latest train schedules and finds the latest predicted time for inbound and outbound trains, leveraging the [MBTA API](https://github.com/mbta/api).

The date & time, along with other useful information are then displayed on the inky pHAT.

## Dependencies

The dependencies that are required are provided in python/requirements.txt. They can be installed with your package manageer of choice.

Numpy version 2.0.0 requires that the system has the OpenBlas System library.

`sudo apt-get install libopenblas-dev`

Note: If you are not using a Raspberry Pi with an inky display, only the *requests* package is required.

## Running the Software

To run the software with a Raspberry Pi that has an inky display, run the instantmbta script:

`python3 instantmbta.py Route_ID, Route_Name, Stop1_ID, Stop1_Name, Stop2_ID, Stop2_Name`

To run the software without a Raspberry Pi with an inky display, simply run the infogather script:

`python3 infogather.py Route_ID, Route_Name, Stop1_ID, Stop1_Name, Stop2_ID, Stop2_Name`

Encapsulate Route_Name, Stop1_Name and Stop2_Name in quotes if name has spaces. (e.g. "A Place") See [The MBTA V3 API](https://www.mbta.com/developers/v3-api) for more information on determining the route and stop ID." Route_Name, Stop1_Name and Stop2_Name are human-readable names that will accompany the results for the provided IDs.
