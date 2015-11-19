# ale-collector

This is a set of sample python scripts that demonstrates the type of
information collected/calculated by ALE.  It shows the usage of both the 
polling API (restapi) as well as the pub/sub (zmq) interfaces.

The information collected is stored in a PostgreSQL DB for future analysis.  

##Content

This package contains the following script.

##Library Files

     restapi.py       - Library for using the ALE RESTAPI
     ale_dbi.py       - Library for storing/retrieving historic
                             information to a PostgreSQL DB
     ale_enums.py	  - ALE constants definitions
	 oui.py			  - Library to print out manufacter's OUI for mac addresses
	 oui.txt		  - OUI DB downloaded from IEEE


## Program Files
     config.py        - Configuration script that turns on/off various
                        features (including the ALE's IP, userid, password)
	 ale-reader.py	  - Subscribes to both ALE's restapi and pub/sub interfaces
	 								and displays feed on-screen

     ale-collector.py - Subscribes to both ALE's restapi and pub/sub interfaces,
	 					displays information on screen and store in DB.
						
	 analyse_ale_collector.py - Simple script to analyse data in DB
	 update_ale_collector_stats.py - Analyse data in DB and store aggregated results in DB

## Support Files
     schema.proto   - The Google Protobuf schema definition for the pub/sub interface
     ale-psql.sql     - The SQL commands to create all the necessary table

     schema_pb2.py    - Library for ALE's protobuf definitions.
                        Generated from 'schema.proto'.

## QuickStart

### Scripts Installation

Please see file INSTALL.rst for instructions for installing the modules that are needed
for these to run.

Edit 'config.py' to configure ALE as well as PostgreSQL servers IP addresses and credentials.

### Database Initiation

If you want to store data feed using ale-collector.py, you need access to postgres DB.
It can be the same server that you're running these scripts on, or on a remore server.

The credentials for accessing the DB (hostname,IP,username,passwd,etc) needs to be 
entered in the 'config.py' file

#### Initialize the DB

The database schema used for these scripts is in the file 'ale-psql.sql'.  For first time
use, the DB tables must be created with the commands:

	psql -h <PostgreSQL Hostname/IP> <database name> < ale-psql.sql

To delete the entire DB and re-initialize 

	dropdb ale
	createdb ale
	psql -h <PostgreSQL Hostname/IP> <database name> < ale-psql.sql

## Usage

python restapi.py

python ale-reader.py -?

python ale-collector.py

## Additional Notes

ALE Message Types (pub/sub) that are supported:

	location
	presence
	rssi
	geofence_notify

Populate from RESTAPI
	campus
	building
	floor
	station
	access_point
	radio
	virtual_access_point

TODO:

High
	campus
	building
	floor
	access_point
	radio
	virtual_access_point

Medium

	station

Low
	
	destination
	application
	visibility_rec
	geofence





