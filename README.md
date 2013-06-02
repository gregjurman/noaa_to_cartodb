NOAA to CartoDB
===============

NOAA to CartoDB converts the NOAA/NWS Shapefiles for severe weather
warnings into Well-Known Text format and then pushes them up to CartoDB
replacing the existing data.

Using
-----
This script requires a few python modules:

* sh
* requests
* Shapely
* cartodb

It also requires Quantum GIS and QGIS's python module installed.

Set your API_KEY and cartodb_domain in config.py then run
update_weather.py
