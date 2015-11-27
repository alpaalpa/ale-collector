#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# config.py
#
# This file is for sharing global variables between modules.
# 

print "Importing Global Config from File: %s" % (__file__)

verbose = 2
ale_host = "10.74.48.21"
ale_nbapi_port = "7779"
# ale_nbapi_port = "7779"   # 7779 is standard.
# ale_nbapi_port = "7778"   # 7778 is sta_rssi (vbr) for ALE 2.0
# ale_nbapi_port = "7777"   # 7777 is sta_rssi (rtls)for ALE 2.0
# ale_nbapi_port = "7776"   # 7776 is ap_rssi (vbr)for ALE 2.0


ale_use_https = True
if ale_use_https:
    ale_restapi_port = "443"
else:
    ale_restapi_port = "8080"

ale_user = "admin"
ale_passwd = "welcome123"


# For SQLite
db_file = 'ale.db'
# For PostgreSQL
# DBI connection to CPPM Postgres DB
db_host = 'localhost'
#db_host = '172.18.164.250'
db_userid = 'apang'
db_password = ''
db_name = 'ale'

# Enable which messages to be stored in DB.  To prevent the DB from getting too big


# Master switch
# If set to False, nothing (including Endpoint) will be stored in DB
# If set to True, store endpoints as well as all info retrieved by the RESTAPI such as
# campus, building, floor, ap, radio, vap in DB
storeInDB = True

# Turn on messages retrieved from the pub/sub interfaces in DB
storeLocationInDB = True
storePresenceInDB = True
storeProximityInDB = True
storeRSSIInDB = False       # Need to turn on the Recipe "Publish RSSI to NBAPI" in ALE as well
storeGeofenceNotifyInDB = True
#
#

timezone = 'Asia/Hong_Kong'
timezoneOffset = 8*60 # Timezone off-set from UTC. In Minutes. As there are some places works on 1/2 hour off-set (e.g. India)
                    # HK is +8h
timezoneOffsetInSeconds = timezoneOffset * 60


