#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# ale-collector.py
#
#
# This is a daemon which subscribes to an pub/sub feed from ALE. It will
# - Update Endpoint table
# - Add location history in Location table
# - Trigger notifications based on rules

# Created: Albert Pang (apang@arubanetworks.com) Apr 9, 2014
# 

"""
 TODO

 Message types:
 
 rssi
 - Check if mac address exists in Endpoint
     if not, add in Endpoint DB
 - Update lastHeardTime
 - Update maxRSSI
 
 geofence_notify
 - Check if mac address exists in Endpoint
     if not, add in Endpoint DB
"""

# Default parameters.  Will be overriden by value set in config file

verbose = 1
ale_host = "localhost"
ale_use_https = True
if ale_use_https:
    ale_restapi_port = "443"
else:
    ale_restapi_port = "8080"

ale_user = "admin"
ale_passwd = "welcome123"

storeInDB = True    # whether to store values in DB

# PostgreSQL
# DBI connection to CPPM Postgres DB
db_host = 'localhost'
db_userid = 'apang'
db_password = ''
db_name = 'ale'


storeLocationInDB = True
storePresenceInDB = True
storeProximityInDB = True
storeRSSIInDB = True       # Need to turn on the Recipe "Publish RSSI to NBAPI" in ALE as well
storeGeofenceNotifyInDB = True
#
#

timezone = 'Asia/Hong_Kong'
timezoneOffset = 8*60 # Timezone off-set from UTC. In Minutes. As there are some places works on 1/2 hour off-set (e.g. India)
                    # HK is +8h


try:
    import config   # Config file.  Global variable definitions
    try: 
        verbose = config.verbose
    except AttributeError: pass
    try:
        ale_host = config.ale_host
    except AttributeError: pass
    try:
        ale_restapi_port = config.ale_restapi_port
    except AttributeError: pass
    try:
        ale_nbapi_port = config.ale_nbapi_port
    except AttributeError: pass
    try:
        ale_user = config.ale_user
    except AttributeError: pass
    try:
        ale_passwd = config.ale_passwd
    except AttributeError: pass
    try:
        storeInDB = config.storeInDB
    except AttributeError: pass        
    try:
         db_host = config.db_host
    except AttributeError: pass        
    try:
         db_userid = config.db_userid
    except AttributeError: pass        
    try:
         db_passwd = config.db_passwd
    except AttributeError: pass        
    try:
         db_name = config.db_name
    except AttributeError: pass        
    try:
        storeLocationInDB = config.storeLocationInDB
    except AttributeError: pass        
    try:
        storePresenceInDB = config.storePresenceInDB
    except AttributeError: pass        
    try:
        storeProximityInDB = config.storePresenceInDB
    except AttributeError: pass        
    try:
        storeRSSIInDB = config.storeRSSIInDB
    except AttributeError: pass        
    try:
        storeGeofenceNotifyInDB = config.storeGeofenceNotifyInDB
    except AttributeError: pass        
    try:
        timezone = config.timezone
    except AttributeError: pass        
    try:
        timezoneOffset = config.timezoneOffset
    except AttributeError: pass        
except ImportError:
    pass

timezoneOffsetInSeconds = timezoneOffset * 60

import sys
# See http://wklken.me/posts/2013/08/31/python-extra-coding-intro.html
reload(sys)
sys.setdefaultencoding('utf-8')

import google.protobuf as pb
from google.protobuf import text_format as txf
import json
import pprint
import ale_pprint
import zmq
import re
import string
import schema_pb2 as loco_pb2
import sys,getopt
import datetime,time
import pytz
import math
import socket, struct
import httplib, urllib

# Now Custom stuff
import ale_enums
import ale_dbi
import restapi
import oui

class Logger(object):
    def __init__(self, filename="ale-collector.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

def convert_mac_fmt(in_mac_addr):
    mac_addr = in_mac_addr.get('addr', None)
    mac_custom.word_fmt = '%.2x'
    mac = str(EUI(mac_addr, dialect=mac_custom))
    return(mac)

def processGeofenceNotifyMsg(cnt,msg):
    """
Note that the use of the 'geofence_notify' message is very different in 1.3 and 2.x.
1.x implementation is specificaly for one customer.  It's based on 'proximity' to 
an AP.  And the list of AP needs to be manually defined.
In 2.x, geofence_notify is based on geofences that are defined either in NAO Cloud or in
AWMS.
Hence, the attributes in these message is very different.
    """    
    
    global conn
    gn = msg.geofence_notify
    macaddr = str(":".join("%02x" % ord(a) for a in gn.sta_mac.addr))

    geofence_event_str = "UNKNOWN"
    if gn.geofence_event == loco_pb2.geofence_notify.ZONE_IN:
        geofence_event_str = "ZONE_IN"
    if gn.geofence_event == loco_pb2.geofence_notify.ZONE_OUT:
        geofence_event_str = "ZONE_OUT"

#        if verbose >= 1:
#            print "---- GEOFENCE_NOTIFY ZONE_OUT [record %.5d: %s] --(ignored)---------" % (cnt, macaddr)
#        return # For now ignore the ZONE_OUT message

    utctimestamp = msg.timestamp - timezoneOffsetInSeconds
    timestamp = datetime.datetime.fromtimestamp(utctimestamp).strftime('%Y-%m-%d %H:%M:%S')

    # Have no idea why we do this:
    geofence_id = 0
    for a in gn.geofence_id:
        geofence_id = (geofence_id << 8) + ord(a)

    geofence_name = gn.geofence_name
    try:
        isAssociated = gn.associated
    except ValueError: isAssociated = None
    
    dwell_time = gn.dwell_time  # ignore this for now
    
    # NOTE: There can be more then 1 Access_point_info element in a message.  One from 
    # each AP.  However, will ignore for now. Or there might not be anything
    
#    ap_mac = gn.access_point_info.ap_mac
#    print ap_mac
#    ap_mac_addr = ap_mac.addr
#    print ap_mac_addr
    has_ap_info = False
    try:
        ap_wired_mac_bin = gn.access_point_info[0].ap_mac.addr
        has_ap_info = True
    except IndexError: 
        pass
    if has_ap_info:
        ap_wired_mac = str(":".join("%02x" % ord(a) for a in ap_wired_mac_bin))
        ap_name = gn.access_point_info[0].ap_name
        bssid_bin = gn.access_point_info[0].radio_bssid.addr
        bssid = str(":".join("%02x" % ord(a) for a in bssid_bin))
        rssi = gn.access_point_info[0].rssi_val
    
        if rssi >= 100: # Bogus value
            rssi = 0
    
    if verbose >= 1:
        print "---- GEOFENCE_NOTIFY %s [record %.5d : %s] ------------" % (geofence_event_str, cnt, macaddr)
        if verbose >= 2:
            print "Timestamp:    %s" % (timestamp)
            print "Station Mac:  %s" % (macaddr)
            print "Geofence Name:%s" % (geofence_name)
            print "Dwell Time: %5d" % (dwell_time)
            if has_ap_info:
                print "Associated:   %s" % (isAssociated)
                print "Detecting AP: %s" % (ap_name)
                print "AP Wired Mac: %s" % (ap_wired_mac)
                print "BSSID:        %s" % (bssid)
                print "RSSI:         %s" % (rssi)

#    if storeInDB:
#        endpoint_id = ale_dbi.updateEndpointByMac(conn,macaddr,'geofence_notify',isAssociated,rssi)

    # ============ Add in code to insert Geofence_Notify entry in DB.
#    if storeInDB and storeGeofenceNotifyInDB:
#        ale_dbi.addGeofenceNotify(conn,endpoint_id,timestamp,geofence_name,ap_name,bssid,rssi)

    return('SUCCESS','')

def processLocationMsg(cnt, msg):
    global conn

    location = msg.location    
    # unpack mac address
    macaddr = str(":".join("%02x" % ord(a) for a in location.sta_eth_mac.addr))
    try:
        measured_x = float(location.sta_location_x)
    except ValueError:
        measured_x = 0.0
    try:
        measured_y = float(location.sta_location_y)
    except ValueError:
        measured_y = 0.0
    isAssociated = location.associated

    utctimestamp = msg.timestamp - timezoneOffsetInSeconds
    timestamp = datetime.datetime.fromtimestamp(utctimestamp).strftime('%Y-%m-%d %H:%M:%S')

    algo_str = "Unknown"
    algo_str = ale_enums.algorithm[location.loc_algorithm]

    # for hex encoded strings, use <thing>.encode("hex")
    floor_id = location.floor_id.encode("hex").upper()
    building_id = location.building_id.encode("hex").upper()
    campus_id = location.campus_id.encode("hex").upper()
    

    if location.HasField("unit"):
        unit = location.unit    
    else:
        unit = None
    
    if storeInDB:
        floor_db_id = ale_dbi.floorIDToDBID(conn,floor_id)
        building_db_id = ale_dbi.buildingIDToDBID(conn,building_id)
        campus_db_id = ale_dbi.campusIDToDBID(conn,campus_id)
        if campus_db_id == 0: 
            campus_db_id = ale_dbi.updateCampus(conn,campus_id,"UNKNOWN",server_id)
        if building_db_id == 0:
            building_db_id = ale_dbi.updateBuilding(conn,building_id,"UNKNOWN",campus_db_id)
        if floor_db_id == 0:
            floor_db_id = ale_dbi.updateFloor(conn,floor_id,"UNKNOWN",None,None,None,None,None,building_db_id,None,None,None)
    else:
        floor_db_id = 0
        building_db_id = 0
        campus_db_id = 0

    if verbose >= 1:
        print "---- LOCATION [record %.5d : %s] ------------" % (cnt, macaddr)
        if verbose >= 2:
            print "Timestamp:    %s (UTC)" % timestamp
            print "Coordinates:  (%.1f, %.1f) " % (measured_x, measured_y)
            if unit != None:
                print "Unit:         %s " % (ale_enums.measurement_unit[unit])
            print "Algorithm:    %s" % (algo_str)
            print "Station Mac:  %s" % (macaddr)
            print "Associated:   %s" % (isAssociated)
            print "FloorID:      %s (%d)" % (floor_id, floor_db_id)
            print "BuildingID:   %s (%d)" % (building_id, building_db_id)
            print "CampusID:     %s (%d)" % (campus_id, campus_db_id)


    if storeInDB:
        endpoint_id = ale_dbi.updateEndpointByMac(conn,macaddr,'location',isAssociated)

        if storeLocationInDB:
            ale_dbi.addLocation(conn,endpoint_id,timestamp,
                ale_dbi.campusIDToDBID(conn,campus_id),
                ale_dbi.buildingIDToDBID(conn,building_id),
                ale_dbi.floorIDToDBID(conn,floor_id),
                measured_x,
                measured_y,
                location.loc_algorithm)
        
    return('SUCCESS','')

def processRSSIMsg(cnt,msg):
    global conn
    
    rssi = msg.rssi # In ALE 1.x, the message is 'rssi', in ALE 2.0 message is 'sta_rssi'
    msgType = 'rssi'

    # For ALE 2.0, the message for Station RSSI has changed from 'rssi' to 'sta_rssi'
    if not rssi.HasField('sta_eth_mac'):
        rssi = msg.sta_rssi

    utctimestamp = msg.timestamp - timezoneOffsetInSeconds
    timestamp = datetime.datetime.fromtimestamp(utctimestamp).strftime('%Y-%m-%d %H:%M:%S')

    macaddr = str(":".join("%02x" % ord(a) for a in rssi.sta_eth_mac.addr))
    isAssociated = rssi.associated
    
#    ap_mac = gn.access_point_info.ap_mac
#    print ap_mac
#    ap_mac_addr = ap_mac.addr
#    print ap_mac_addr

    radio_mac = str(":".join("%02x" % ord(a) for a in rssi.radio_mac.addr))

    rssi_val = rssi.rssi_val
    
    if rssi_val > 100:  # Something is wrong from ALE.  Ignore the value
        rssi_val = 0;

    # ALE 2.0 has these extra fields
    age = None
    noise_floor = None
    assoc_bssid = None
    
    try:
        rssi.HasField('age')
        age = rssi.age
    except ValueError:
        pass
    try:
        rssi.HasField('noise_floor')
        noise_floor = rssi.noise_floor
    except ValueError:
        pass
    try:
        rssi.HasField('assoc_bssid')
        assoc_bssid = str(":".join("%02x" % ord(a) for a in rssi.assoc_bssid.addr))
    except ValueError:
        pass

    if storeInDB:
        ap_id = ale_dbi.getAPIdByRadioMac(conn,radio_mac)
        (ap_wired_mac,ap_name) = ale_dbi.getAPNameById(conn,ap_id)
    else:
        ap_id = 0
        ap_wired_mac = ""
        ap_name = ""
    
    if verbose >= 1:
        print "---- RSSI [record %.5d : %s] ------------" % (cnt, macaddr)
        if verbose >= 2:
            print "Timestamp:         %s (UTC)" % (timestamp)
            print "Station Mac:       %s" % (macaddr)
            print "Associated:        %s" % (isAssociated)
            print "Radio Mac:         %s" % (radio_mac)
            if storeInDB:
                print "AP Wired Mac:      %s (%s)" % (ap_wired_mac,ap_name)
            print "RSSI:             %4d" % (rssi_val)
            if age:
                print "Age:              %4d" % (age)
            if noise_floor:
                print "Noise Floor:      %4d" % (noise_floor)
            if assoc_bssid:
                print "Associated BSSID:  %s (%s)" % (assoc_bssid,oui.getVendor(assoc_bssid))
                
    if storeInDB:
        endpoint_id = ale_dbi.updateEndpointByMac(conn,macaddr,'rssi',isAssociated,rssi_val)
        if storeRSSIInDB:
            radio_id = ale_dbi.getRadioIdByMac(conn,radio_mac)
            ale_dbi.addRSSI(conn,endpoint_id,timestamp,radio_id,rssi_val,isAssociated,age,noise_floor,assoc_bssid)
        
    return('SUCCESS','')
    
def processPresenceMsg(cnt,msg):
    global conn
    
    presence = msg.presence
    
    utctimestamp = msg.timestamp - timezoneOffsetInSeconds
    timestamp = datetime.datetime.fromtimestamp(utctimestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    macaddr = str(":".join("%02x" % ord(a) for a in presence.sta_eth_mac.addr))
    isAssociated = presence.associated
    ap_name = None
    try:
        ap_name = presence.ap_name
    except AttributeError: pass
    # print "ap_name=", ap_name
    radio_mac = None
    try:
        radio_mac = str(":".join("%02x" % ord(a) for a in presence.radio_mac.addr))
    except AttributeError: pass
    if storeInDB and radio_mac:
        radio_id = ale_dbi.getAPIdByRadioMac(conn,radio_mac)

    if verbose >= 1:
        print "---- PRESENCE [record %.5d : %s] ------------" % (cnt, macaddr)
        if verbose >= 2:
            print "Timestamp:    %s (UTC)" % (timestamp)
            print "Station Mac:  %s" % (macaddr)
            print "Associated:   %s" % (isAssociated)

            if radio_mac:
                print "Radio Mac:    %s" % (radio_mac)                

            if ap_name:
                ap_name = ap_name.encode('utf-8')
                print "Detecting AP Name: %s" % (ap_name,)
                print "PRESENCE Summary,%s,%s,%s" % (timestamp,macaddr,presence.associated)
            else:
                print "PRESENCE Summary,%s,%s,%s" % (timestamp,macaddr,presence.associated)

    if storeInDB:
        radio_id = ale_dbi.getAPIdByRadioMac(conn,radio_mac)
        # print "radio_id = ", radio_mac, radio_id
        endpoint_id = ale_dbi.updateEndpointByMac(conn,macaddr,'presence',isAssociated)
        if storePresenceInDB:
            ale_dbi.addPresence(conn,endpoint_id,timestamp,isAssociated,ap_name,radio_id,server_id)

    return('SUCCESS','')

def processProximityMsg(cnt,msg):
    global conn
    
    proximity = msg.proximity
    
    utctimestamp = msg.timestamp - timezoneOffsetInSeconds
    timestamp = datetime.datetime.fromtimestamp(utctimestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    macaddr = str(":".join("%02x" % ord(a) for a in proximity.sta_eth_mac.addr))
    ap_name = None
    try:
        ap_name = proximity.ap_name
    except AttributeError: pass
    # print "ap_name=", ap_name
    radio_mac = None
    rssi = 0
    try:
        rssi = proximity.rssi_val
    except AttributeError: pass
    try:
        radio_mac = str(":".join("%02x" % ord(a) for a in proximity.radio_mac.addr))
    except AttributeError: pass
    if storeInDB and radio_mac:
        radio_id = ale_dbi.getAPIdByRadioMac(conn,radio_mac)

    if verbose >= 1:
        print "---- PROXIMITY [record %.5d : %s] ------------" % (cnt, macaddr)
        if verbose >= 2:
            print "Timestamp:    %s (UTC)" % (timestamp)
            print "Station Mac:  %s" % (macaddr)

            if radio_mac:
                print "Radio Mac:    %s" % (radio_mac)                

            if rssi:
                print "RSSI:         %3d" % (rssi)

            if ap_name:
                ap_name = ap_name.encode('utf-8')
                print "Detecting AP: %s" % (ap_name,)
                print "PROXIMITY Summary,%s,%s,%d,%s" % (timestamp,macaddr,rssi,ap_name)
            else:
                print "PROXIMITY Summary,%s,%s,%d" % (timestamp,macaddr,rssi)

    if storeInDB:
        radio_id = ale_dbi.getAPIdByRadioMac(conn,radio_mac)
        # print "radio_id = ", radio_mac, radio_id
        endpoint_id = ale_dbi.updateEndpointByMac(conn,macaddr,'proximity',None,rssi)
        if storeProximityInDB:
            ale_dbi.addPresence(conn,endpoint_id,timestamp,isAssociated=None,ap_name=ap_name,radio_id=radio_id,server_id=server_id,rssi=rssi)

    return('SUCCESS','')



def processStationMsg(cnt,msg):
    global conn
    
    station = msg.station

    utctimestamp = msg.timestamp - timezoneOffsetInSeconds
    timestamp = datetime.datetime.fromtimestamp(utctimestamp).strftime('%Y-%m-%d %H:%M:%S')

    macaddr = str(":".join("%02x" % ord(a) for a in station.sta_eth_mac.addr))
    username = station.username
    role = station.role
    bssid = str(":".join("%02x" % ord(a) for a in station.bssid.addr))
    device_type = station.device_type
    ip_addr = (".".join("%d" % ord(a) for a in station.sta_ip_address.addr))

    if verbose >= 1:
        print "---- STATION [record %.5d : %s] ------------" % (cnt, macaddr)
        if verbose >=2:
            print "Timestamp:    %s (UTC)" % (timestamp)
            print "Station Mac:  %s" % (macaddr)
            print "Username:     %s" % (username)
            print "Role:         %s" % (role)
            print "BSSID:        %s" % (bssid)
            print "Device Type:  %s" % (device_type)
            print "IP Address:   %s" % (ip_addr)

    if storeInDB:
        endpoint_id = ale_dbi.updateEndpointByMac(conn,macaddr,'station')
        ale_dbi.updateEndpointDetails(conn,endpoint_id,username,role,bssid,device_type,ip_addr)

    return('SUCCESS','')

def processAPMsg(cnt,msg):
    global conn
    ap = msg.access_point
    
    if verbose >= 3: print ap
    
    ap_eth_mac = str(":".join("%02x" % ord(a) for a in ap.ap_eth_mac.addr))

    if verbose >= 1:
        print "---- AP [record %.5d : %s] ------------" % (cnt, ap_eth_mac)

    try:
        reboots = ap.reboots
    except AttributeError: reboots = 0
    try:
        rebootstraps = ap.rebootstraps
    except AttributeError: rebootstraps = 0

    ip_str = (".".join("%d" % ord(a) for a in ap.ap_ip_address.addr))

    if storeInDB:
        ap_id = ale_dbi.updateAP(conn,ap_eth_mac,ap.ap_name,ap.ap_group,ap.ap_model,ap.depl_mode,ip_str,reboots,rebootstraps,server_id)
        return ap_id
    else: return 0

def processRadioMsg(cnt,msg):
    global conn
    radio = msg.radio
    
    ap_eth_mac = str(":".join("%02x" % ord(a) for a in radio.ap_eth_mac.addr))
    radio_bssid = str(":".join("%02x" % ord(a) for a in radio.radio_bssid.addr))
    
    if verbose >= 1:
        print "---- RADIO[record %.5d : %s] ------------" % (cnt, radio_bssid)

    try:
        mode = radio.mode
    except AttributeError: mode = None
    try:
        phy = radio.phy
    except AttributeError: phy = None
    try:
        ht = radio.ht
    except AttributeError: ht = None

    if storeInDB:
        ap_id = ale_dbi.getAPIdByMac(conn,ap_eth_mac)
        radio_id = ale_dbi.updateRadio(conn,ap_id,radio_bssid,mode,phy,ht)
        return radio_id
    else: return 0

def processVAPMsg(cnt,msg):
    global conn
    vap = msg.virtual_access_point

    if verbose >= 4:
        print vap

    vap_bssid = vap.bssid

    ssid = vap.ssid
    bssid = str(":".join("%02x" % ord(a) for a in vap.bssid.addr))
    radio_bssid = str(":".join("%02x" % ord(a) for a in vap.radio_bssid.addr))

    if verbose >= 1:
        print "---- VAP [record %.5d : %s] ------------" % (cnt, bssid)
    
    if verbose >= 3:
        print bssid,ssid,radio_bssid

    if storeInDB:
        radio_id = ale_dbi.getRadioIdByMac(conn,radio_bssid)

        # NEED to store it in DB
        vap_id = ale_dbi.updateVAP(conn,radio_id,bssid,ssid)
        return vap_id
    else: return 0
    
# Handles messages from ALE pub/sub
def handleALEEvent(topic,data):
    global countEvent
    global config
    
    aleMsg = loco_pb2.nb_event()
    aleMsg.Clear()
    aleMsg.ParseFromString(data)
    
    #dummy print of topic and msg
    if verbose >= 2:
        print 
        print '*** received an event pub ('+str(countEvent)+') ***'
        print topic
        msg_json = ale_pprint.msgToJSON(aleMsg,level=1,topic=topic)
        print msg_json

    return aleMsg


def main(argv):
    global progname
    global config
    global conn
    
    global countEvent
    global countLocation
    global countPresence
    global countRssi
    global countGeofence
    
    global server_id

    progname=argv[0]

    #set global counters for pub received

    countEvent = 0
    countLocation = 0
    countPresence = 0
    countRssi = 0
    countGeofence = 0
    countProximity = 0

    # These options should be read from command line.  Will implement it later.
    opt_logging = False
    opt_quiet = False
    url = "tcp://%s:%s" % (ale_host, ale_nbapi_port)
    # List of topics that are subscribed.  Listen to all right now by specifying a blank list
    topic_list = []
    topic=''

    # Set-up logging.
    now_str = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    logging_file = 'ale-collector-%s.log' % now_str

    # Set-up DB
    if storeInDB:
        (conn, cursor) = ale_dbi.initDBConnection()
        server_id = ale_dbi.getServerID(conn,ale_host)
    else:
        conn = 0
    
    # Now should retrieve info from RESTAPI
    c = restapi.campus(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved Campus IDs (%d)" % c.size()
    if verbose >= 2: print c
    
    if storeInDB: c.updateDB(conn,server_id)
        
    b = restapi.building(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved Building IDs (%d)" % b.size()
    if verbose >= 2: print b

    if storeInDB: b.updateDB(conn,server_id)


    f = restapi.floor(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved Floor IDs (%d)" % f.size()
    if verbose >= 2: print f    

    if storeInDB: f.updateDB(conn,server_id)
    
    a = restapi.access_point(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of access points (%d)" % a.size()
    if verbose >= 2: print a

    if storeInDB: a.updateDB(conn,server_id)

    r = restapi.radio(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of radios (%d)" % r.size()
    if verbose >= 2: print r

    if storeInDB: r.updateDB(conn)

    v = restapi.virtual_access_point(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of VAP (%d)" % v.size()
    if verbose >= 2: print v
    
    if storeInDB: v.updateDB(conn)
    
    s = restapi.station(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of associated stations (%d)" % s.size()
    if verbose >= 2: print s

    if storeInDB: s.updateDB(conn)
    
    #core of main
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(url)
    subscriber.setsockopt_string(zmq.SUBSCRIBE,unicode(topic))#encoding string from unicod to utf-8
    
    if opt_logging:
        if opt_quiet:
            print "Quiet option enabled. No further output printed on Terminal"
            sys.stdout = open(logging_file, 'w')
        else:  
            sys.stdout = Logger(logging_file)


        # init counts and handlers
    topic_handlers = {
        # ALE 1.3
        "location": (0, processLocationMsg),
        "presence": (0, processPresenceMsg),
        "rssi": (0, processRSSIMsg),
        "station": (0, processStationMsg),
        "radio": (0, processRadioMsg),
        "access_point": (0,processAPMsg),
        "virtual_access_point": (0,processVAPMsg),
        "geofence_notify": (0, processGeofenceNotifyMsg),
        # ALE 1.3 topics. Un-supported or disabled topics:
        "destination": (0, None),
        "application": (0, None),
        "visibility_rec": (0, None),
        "campus": (0, None),
        "building": (0, None),        
        "floor": (0, None),
        "geofence": (0, None),
        # New in ALE 2.0
        "stats_radio": (0, None),
        "stats_vap": (0, None),
        "stats_station": (0, None),
        "ap_neighbor_list": (0, None),
        "utilization_stats_radio": (0, None),
        # "sta_rssi": (0, None), # Treating this as 'rssi'
        "ap_rssi": (0, None),
        "proximity": (0, processProximityMsg),
    }
    
    topic_dict = {}
    done = 0
    
    #forever loop to wait publish
    print 'waiting for zmq sub msg'
    print
        
    while(True):
        try:
            #we know we will receive two messages topic (str) and data (protobuf string to parse)
            topic = subscriber.recv()
            data  = subscriber.recv()
            if not topic_dict.has_key(topic):
                topic_dict[topic] = 1
            else:
                topic_dict[topic] += 1
        
            countEvent += 1

            what_topic = topic

            if verbose >=3:
                print 'TOPIC: ' + topic

            if (topic in topic_list) or (len(topic_list) == 0):
                ap_rssi_p = re.compile('ap_rssi/(.*)')
                sta_rssi_p = re.compile('sta_rssi/(.*)')
                location_p = re.compile('location/(.*)')
                
                msg = handleALEEvent(topic, data)

                match_ap = ap_rssi_p.match(topic)
                match_sta = sta_rssi_p.match(topic)
                match_location = location_p.match(topic)

                if match_ap:
                    short_topic = 'ap_rssi'
                # in ALE 2.0, the Station RSSI feed is changed from 'rssi' to 'sta_rssi', and is streamed
                # from a different port.
                elif match_sta:
                    short_topic = 'rssi'
                elif match_location:
                    short_topic = 'location'
                else:
                    short_topic = topic
            
                if topic_handlers.has_key(short_topic):
                    topic_handlers[short_topic] = (topic_handlers[short_topic][0] + 1, topic_handlers[short_topic][1])
                    # msg processor takes care of output and formatting
                    if topic_handlers[short_topic][1]:
                        topic_handlers[short_topic][1](topic_handlers[short_topic][0], msg)

        except KeyboardInterrupt:
            print "client unsubscribed"
            done = 1

        if not verbose or done:
            keys = topic_dict.keys()
            keys.sort()
            if verbose:
                print "Total %d topics" % len(keys)
            for k in keys:
#                print "\t %-20s %d" % (k, topic_dict[k])
                if done:
                    print >>sys.stderr, "\t %-20s %d" % (k, topic_dict[k])
#            print >>sys.stderr, "max_latency", g_max_latency, "out of %s samples" % topic_handlers["location"][0]
        
        if done:
            sys.stderr.flush()
            break

# if it is run from terminal:true, if it is imported :false
if __name__ == "__main__":
    global conn
    oui.initializeOUITable()
    if storeInDB:
        (conn, cursor) = ale_dbi.initDBConnection()
    else:
        conn = 0
    main(sys.argv)
    

    

    
