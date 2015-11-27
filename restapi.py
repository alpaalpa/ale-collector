#!/usr/bin/env python

"""
########################################################################################################
#
# restapi.py
# 
# Sample Implementation for querying the Aruba Analytics and Location Engine (API) via the RESTAPI.
#
# Author: Albert Pang
# (c) 2015 Aruba Networks
#
# This python module is normally used by other scripts (e.g. ale-reader.py and ale-collector.py)
# but can be used standalone (e.g. for testing)
#
########################################################################################################

Here's a list of API (1.x and 2.x).  Can be access with:

ALE 1.0

http://SERVERIP/api/v1/access_point
http://SERVERIP/api/v1/virtual_access_point
http://SERVERIP/api/v1/station
http://SERVERIP/api/v1/presence
http://SERVERIP/api/v1/campus
http://SERVERIP/api/v1/building
http://SERVERIP/api/v1/floor
http://SERVERIP/api/v1/location?sta_eth_mac=AA:BB:CC:DD:EE:FF
http://SERVERIP/api/v1/application
http://SERVERIP/api/v1/destination
http://SERVERIP/api/v1/geo_fence


ALE 2.0

For ALE 2.x, the preferred transport is https on standard port (tcp/443).
Here are additional API that are introduced in 2.0.

https://SERVERIP/api/v1/info
https://SERVERIP/api/v1/webcc_category
https://SERVERIP/api/v1/topology
https://SERVERIP/api/v1/controller
https://SERVERIP/api/v1/cluster_info
https://SERVERIP/api/v1/proximity


"""


# Sets of local variables defined in this file.  This could be overriden if a config.py file is imported.

verbose = 3

ale_host = "10.74.48.25"
# For ALE 2.0 and above, the prefer method of access is via https.  Also, authentication is mandatory
ale_use_https = True
ale_user = "admin"
ale_passwd = "welcome123"


if ale_use_https:
    ale_restapi_port = "443"
else:
    ale_restapi_port = "8080"

db_host = 'localhost'
db_userid = 'apang'
db_password = ''
db_name = 'ale'

storeInDB = False

err_msg = "Is a license installed on this ALE server? Is userid/password correct"

try:
    import config   # Module where Global Variables are stored
    try: 
        verbose = config.verbose
    except AttributeError: pass
    try:
        ale_host = config.ale_host
    except AttributeError: pass
    try:
        ale_user = config.ale_user
    except AttributeError: pass
    try:
        ale_passwd = config.ale_passwd
    except AttributeError: pass
    try:
        ale_use_https = config.ale_use_https
    except AttributeError: pass
    try:
        ale_restapi_port = config.ale_restapi_port
    except AttributeError: pass
    try:
        db_host = config.db_host
    except AttributeError: pass
    try:
        db_userid = config.db_userid
    except AttributeError: pass
    try:
        db_password = config.db_password
    except AttributeError: pass
    try:
        db_name = config.db_name
    except AttributeError: pass
    try:
        storeInDB = config.storeInDB
    except AttributeError: pass
except ImportError:
    pass

import ale_enums
if storeInDB:
    import ale_dbi

# On an Aruba ALE server, the following packages must be installed before this would run
#   requests, netaddr


import requests
import json
from netaddr import *
from requests.auth import HTTPBasicAuth

ale_auth = HTTPBasicAuth(ale_user,ale_passwd)

http_header={'Accept': 'application/json'}

def retrieveDataFromALE(type,host,port,use_https=ale_use_https):
    if use_https:
        api_url = "https://%s:%s/api/v1/" % (host,port)
    else:
        api_url = "http://%s:%s/api/v1/" % (host,port)            
    # List of valid REST API (as of ALE 1.2). Note that the 'location' API needs special treatment as
    # an argument is mandatory. Is is not supported in this version.
    api_types = ['campus', 'building', 'floor', 'access_point', 'radio', 'application', 'destination', 
                 'station', 'virtual_access_point', 'geofence']
    # define short-cuts
    if type == 'vap':
        type = 'virtual_access_point'
    if type == 'ap':
        type = 'access_point'
        
    # Sucessful call to REST API would return 1 JSON object with a single key.  The key is different depends
    # on the API type. The format is 'Type_result' and so far is consistent.  However, listing each one individually
    # just in case someone decides to do something else.
    
    api_result_keys = {
        'campus': 'Campus_result',
        'building': 'Building_result',
        'floor': 'Floor_result',
        'access_point': 'Access_point_result',
        'radio': 'Radio_result',
        'application': 'Application_result',
        'destination': 'Destination_result',
        'station': 'Station_result',
        'virtual_access_point': 'Virtual_access_point_result',
        'geofence': 'Geofence_result'
    }
    
    if type in api_types:
        get_url = api_url + type
    else:
        e = "Unknown API type: %s" % (type)
        if verbose: print e
        return ({}, e)
        
    try:
        r = requests.get(get_url, headers=http_header, auth=ale_auth, verify=False)
    except requests.exceptions.RequestException as e:    
        if verbose:
            print "Cannot connect to REST host %s on port %s" % (host,port)
            print e
        return ({}, e)

    try:
        data = json.loads(r.content)
    except ValueError:
        e = 'Decoding JSON has failed or this version of ALE server does not support this API'
        if verbose:
            print e
            print err_msg
        return ({},e)

    result_key = api_result_keys[type]
    if data.has_key(result_key):
        result = data[result_key]
    else:
        e = "JSON Data not in correct format. Expecting '%s' as first key" % (result_key)
        if verbose:
            print e
        return ({},e)

    return (result,0)

class campus:
    """This class retrieve all the campuses from ALE"""
    def __init__(self,host,port):
        self.campuses = {}
        self.campuses_ts = {}
        self.count = 0
        
        (campus_result,error) = retrieveDataFromALE('campus',host,port)        

        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(campus_result)

        for i,msg in enumerate(campus_result):
            msg_content = msg['msg']
            campus_id = msg_content['campus_id']
            ts = msg.get('ts',None)
            campus_name = msg_content['campus_name']
            self.campuses[campus_id] = campus_name
            self.campuses_ts[campus_id] = ts

    def __str__(self):  
        padding = 32 - len("Campus ID")
        all_campus_str = "Items in campus class: %d\n" % self.count
        if self.count >= 1:
            all_campus_str = all_campus_str + "Campus ID%s\tCampus Name\n" % (" " * padding)
            for campus_id in self.campuses:
                campus_str = "%s\t%s\n" %(campus_id,self.campuses[campus_id])
                all_campus_str = all_campus_str + campus_str
        return all_campus_str

    def getName(campus_id):
        return self.campuses.get(campus_id, 'Unknown')

    def size(self):
        """Rerutn the number campuses read"""
        return self.count
        
    if storeInDB:
        def updateDB(self,conn,server_id):
            for campus_id in self.campuses:
                ale_dbi.updateCampus(conn,campus_id,self.campuses[campus_id],server_id)
            
class building:
    def __init__(self,host,port):
        self.buildings = {}
        self.buildings_ts = {}
        self.buildings_campus_id = {}
        self.count = 0
        
        (building_result, error) = retrieveDataFromALE('building',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(building_result)

        for i,msg in enumerate(building_result):
            msg_content = msg['msg']
            ts = msg.get('ts',None)
            building_id = msg_content['building_id']
            building_campus_id = msg_content['campus_id']
            building_name = msg_content['building_name']
            self.buildings[building_id] = building_name
            self.buildings_ts[building_id] = ts
            self.buildings_campus_id[building_id] = building_campus_id

    def __str__(self):  
        padding = 32 - len("Building ID")
        all_building_str = "Items in building class: %d\n" % self.count
        if self.count >= 1:
            all_building_str = all_building_str + "Building ID%s\tBuilding Name\tCampus ID\n" %(" " * padding)
            for building_id in self.buildings:
                building_str = "%s\t%s\t%s\n" %(building_id,self.buildings[building_id],self.buildings_campus_id[building_id])
                all_building_str = all_building_str + building_str
        return all_building_str
        
    def getName(building_id):
        return self.buildings.get(building_id, 'Unknown')


    def size(self):
        return self.count

    if storeInDB:
        def updateDB(self,conn,server_id):
            cursor = conn.cursor()
            
            for building_awms_id in self.buildings:
                name = self.buildings[building_awms_id]
                campus_awms_id = self.buildings_campus_id[building_awms_id]
                campus_id = ale_dbi.campusIDToDBID(conn,campus_awms_id)
                ale_dbi.updateBuilding(conn,building_awms_id,name,campus_id)

class floor:
    def __init__(self,host,port):
        self.floors = {}
        self.floors_ts = {}
        self.floors_building_id = {}
        self.floors_latitude = {}
        self.floors_longitude = {}
        self.floors_img_path = {}
        self.floors_img_width = {}
        self.floors_img_length = {}
        self.floors_level = {}
        self.floors_units = {}
        self.floors_grid_size = {}
        self.count = 0
        
        (floor_result,error) = retrieveDataFromALE('floor',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(floor_result)

        for i,msg in enumerate(floor_result):
            msg_content = msg['msg']
            ts = msg.get('ts',None)
            floor_id = msg_content.get('floor_id',None)
            floor_name = msg_content.get('floor_name',"UNKNOWN")
            floor_latitude = msg_content.get('floor_latitude',None)
            floor_longitude = msg_content.get('floor_longitude',None)
            floor_img_path = msg_content.get('floor_img_path',None)
            floor_img_width = msg_content.get('floor_img_width',None)
            floor_img_length = msg_content.get('floor_img_length',None)
            floor_building_id = msg_content.get('building_id',None)
            floor_level = msg_content.get('floor_level',None)
            floor_units = msg_content.get('units',None)
            floor_grid_size = msg_content.get('grid_size',0)
            self.floors_ts[floor_id] = ts
            self.floors[floor_id] = floor_name
            self.floors_latitude[floor_id] = floor_latitude
            self.floors_longitude[floor_id] = floor_longitude
            self.floors_img_path[floor_id] = floor_img_path
            self.floors_img_width[floor_id] = floor_img_width
            self.floors_img_length[floor_id] = floor_img_length
            self.floors_building_id[floor_id] = floor_building_id
            self.floors_level[floor_id] = floor_level
            self.floors_units[floor_id] = floor_units
            self.floors_grid_size[floor_id] = floor_grid_size


    def __str__(self):  
        padding = 32 - len("Floor ID")
        all_floor_str = "Items in floor class: %d\n" % self.count
        if self.count >= 1:
            all_floor_str = all_floor_str + "Floor ID%s\tFloor Name\tBuilding ID\tImg(width,length)\tGrid Size\tUnits\n" %(" " * padding)
            for floor_id in self.floors:
                floor_str = "%s\t%s\t%s\t(%d,%d)\t[%.1f]\t%s\n" %(floor_id,self.floors[floor_id],self.floors_building_id[floor_id],
                    self.floors_img_width[floor_id],self.floors_img_length[floor_id],self.floors_grid_size[floor_id],self.floors_units[floor_id])
                all_floor_str = all_floor_str + floor_str
        return all_floor_str
        
    def getName(floor_id):
        return self.floors.get(floor_id, 'Unknown')

    def size(self):
        return self.count
        
    if storeInDB:
        def updateDB(self,conn,server_id):
            cursor = conn.cursor()
            
            for floor_awms_id in self.floors:
                name = self.floors[floor_awms_id]
                latitude = self.floors_latitude[floor_awms_id]
                longitude = self.floors_longitude[floor_awms_id]
                img_path = self.floors_img_path[floor_awms_id]
                img_width = self.floors_img_width[floor_awms_id]
                img_length = self.floors_img_length[floor_awms_id]
                building_awms_id = self.floors_building_id[floor_awms_id]
                building_id = ale_dbi.buildingIDToDBID(conn,building_awms_id)
                if building_id == 0:
                    campus_id = ale_dbi.updateCampus(conn,"UNKNOWN","UNKNOWN",server_id)
                    building_id = ale_dbi.updateBuilding(conn,building_awms_id,"UNKNOWN",campus_id)
                
                level = self.floors_level[floor_awms_id]
                units = self.floors_units[floor_awms_id]
                grid_size = self.floors_grid_size[floor_awms_id]

                ale_dbi.updateFloor(conn,floor_awms_id,name,latitude,longitude,img_path,img_width,img_length,building_id,level,units,grid_size)
                
class access_point:
    def __init__(self,host,port):
        self.access_points_name = {}
        self.access_points_group = {}
        self.access_points_model = {}
        self.access_points_depl_mode = {}
        self.access_points_ip_address = {}
        self.access_points_ts = {}
        self.count = 0
        
        (access_point_result,error) = retrieveDataFromALE('access_point',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(access_point_result)

        for i,msg in enumerate(access_point_result):
            msg_content = msg['msg']
            ts = msg.get('ts',None)
            ap_mac_addr = msg_content['ap_eth_mac']

            mac_addr = ap_mac_addr.get('addr', None)
            mac_custom.word_fmt = '%.2x'
            mac = str(EUI(mac_addr, dialect=mac_custom))
            access_point_mac_addr = mac
            access_point_name = msg_content.get('ap_name',None)
            if access_point_name:
                access_point_name = access_point_name.encode('utf-8')
            access_point_group = msg_content.get('ap_group',None)
            if access_point_group:
                access_point_group = access_point_group.encode('utf-8')
            access_point_model = msg_content.get('ap_model',None)
            if access_point_model:
                access_point_model = access_point_model.encode('utf-8')
            access_point_depl_mode = msg_content.get('depl_mode',None)
            if access_point_depl_mode:
#                access_point_depl_mode = access_point_depl_mode.encode('utf-8')
                access_point_depl_mode = ale_enums.deployment_mode.index(access_point_depl_mode.encode('utf-8'))

            ap_ip_address = msg_content.get('ap_ip_address',None)
            if ap_ip_address:
                access_point_ip_address = ap_ip_address.get('addr', None)
                if access_point_ip_address:
                    access_point_ip_address = access_point_ip_address.encode('utf-8')

            self.access_points_name[access_point_mac_addr] = access_point_name
            self.access_points_group[access_point_mac_addr] = access_point_group
            self.access_points_model[access_point_mac_addr] = access_point_model
            self.access_points_depl_mode[access_point_mac_addr] = access_point_depl_mode
            self.access_points_ip_address[access_point_mac_addr] = access_point_ip_address
            self.access_points_ts[access_point_mac_addr] = ts

    def __str__(self):  
        all_ap_str = "Number of Access Points: %d\n" % self.count
        if self.count >= 1:
            all_ap_str = all_ap_str + "ap_eth_mac       \tap_name\tap_group\tip_address\tmodel\tdepl_mode\n"
            for mac in sorted(self.access_points_name.iterkeys()):
                ap_str = "%s\t%s\t%s\t%s\t%s\t%s\n" % (mac,self.access_points_name[mac],
                    self.access_points_group[mac],self.access_points_ip_address[mac],self.access_points_model[mac],
                    ale_enums.deployment_mode[self.access_points_depl_mode[mac]])
                """
                ap_str = "%s\t%s\t%s\t%s\n" % (mac,self.access_points_name[mac],
                    self.access_points_group[mac],self.access_points_ip_address[mac])
                """
                all_ap_str = all_ap_str + ap_str
        return all_ap_str
    def size(self):
        return self.count
    
    if storeInDB:
        def updateDB(self,conn,server_id):
            cursor = conn.cursor()
        
            for access_point_mac_addr in self.access_points_name:

                ale_dbi.upsert(cursor, 'AP', ('macAddress',), schema=None, macAddress=access_point_mac_addr, name=self.access_points_name[access_point_mac_addr])

                params = (access_point_mac_addr,)
                cursor.execute("SELECT id FROM AP WHERE macAddress = %s", params)
                row = cursor.fetchone()
                if row == None:
                    print "access_point.updateDB(): Error in DB"
                else:
                    ap_id = row[0]

                name = self.access_points_name[access_point_mac_addr]
                apGroup = self.access_points_group[access_point_mac_addr]
                model = self.access_points_model[access_point_mac_addr]
                mode = self.access_points_depl_mode[access_point_mac_addr]
                ip = self.access_points_ip_address[access_point_mac_addr]
                params = (name,apGroup,model,mode,ip,server_id,ap_id)
                cursor.execute("UPDATE AP SET name=%s,apGroup=%s,model=%s,mode=%s,ip=%s,server_id=%s WHERE id = %s", params)
            conn.commit()

def convert_mac_fmt(in_mac_addr):
    mac_addr = in_mac_addr.get('addr', None)
    mac_custom.word_fmt = '%.2x'
    mac = str(EUI(mac_addr, dialect=mac_custom))
    return(mac)

class radio:
    def __init__(self,host,port):
        # Dictionaries with bssid as keys
        self.radios_wired_mac = {}
        self.radios_ht_type = {}
        self.radios_mode = {}
        self.radios_phy_type = {}
        self.radios_ts = {}
        self.count = 0
        
        (radio_result, error) = retrieveDataFromALE('radio',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(radio_result)

        for i,msg in enumerate(radio_result):
            msg_content = msg['msg']
            ts = msg.get('ts',None)
            radio_bssid = msg_content['radio_bssid']
            # Sometime between ALE 1.0 and 1.2, this 'key' has changed to 'ap_eth_mac'
            ap_mac_addr = msg_content['ap_eth_mac']

            bssid = str(convert_mac_fmt(radio_bssid))
            wired_mac = str(convert_mac_fmt(ap_mac_addr))
#            phy_type = msg_content['phy_type']
            phy_type_str = msg_content['phy']
            phy_type = ale_enums.phy_type.index(phy_type_str.replace('RADIO_', ''))
            mode_str = msg_content['mode']
            mode = ale_enums.radio_mode.index(mode_str)
            ht_type_str = msg_content['ht']
            ht_type = ale_enums.ht_type.index(ht_type_str)

            # print "BSSID: [%s] Wired Mac: [%s] Phy_type: %s Mode: %s" % (bssid, wired_mac, phy_type, mode)

            self.radios_wired_mac[bssid] = wired_mac
            self.radios_phy_type[bssid] = phy_type
            self.radios_mode[bssid] = mode
            self.radios_ts[bssid] = ts
            self.radios_ht_type[bssid] = ht_type

    def __str__(self):  
        all_radio_str = "Number of Radios: %d\n" % self.count
        if self.count >= 1:
            all_radio_str = all_radio_str + "bssid\twired_mac\tphy_type\tmode\tht\n"
            for bssid in sorted(self.radios_wired_mac.iterkeys()):
                bssid_str = "%s\t%s\t%s\t%s\t%s\n" % (bssid,self.radios_wired_mac[bssid],
                    ale_enums.phy_type[self.radios_phy_type[bssid]],
                    ale_enums.radio_mode[self.radios_mode[bssid]],
                    ale_enums.ht_type[self.radios_ht_type[bssid]],
                    )
                all_radio_str = all_radio_str + bssid_str
        return all_radio_str

    if storeInDB:
        def updateDB(self,conn):
            cursor = conn.cursor()
    
            for bssid in self.radios_wired_mac:
                ale_dbi.upsert(cursor, 'Radio_BSSID', ('radio_bssid',), schema=None, radio_bssid=bssid,mode=self.radios_mode[bssid])

                params = (bssid,)            
                cursor.execute("SELECT id FROM Radio_BSSID WHERE radio_bssid = %s", params)
                row = cursor.fetchone()
                if row == None:
                    print "radio.updateDB(): Error in DB"
                else:
                    bssid_id = row[0]
                
                wired_mac = self.radios_wired_mac[bssid]
                phy_type = self.radios_phy_type[bssid]
                ht_type = self.radios_ht_type[bssid]
                mode = self.radios_mode[bssid]
                ts = self.radios_ts[bssid]
                ap_id = ale_dbi.getAPIdByMac(conn,wired_mac)
                if ap_id == 0:
                    params = (wired_mac,"UNKNOWN","UNKNOWN")
                    cursor.execute("INSERT INTO AP (macaddress,name,apGroup) VALUES (%s,%s,%s)", params)
                    ap_id = ale_dbi.getAPIdByMac(conn,wired_mac)
                
                params = (phy_type,mode,ht_type,ap_id,bssid_id)
                cursor.execute("UPDATE Radio_BSSID SET phyType=%s,mode=%s,ht=%s,ap_id=%s WHERE id=%s",params)
            conn.commit()

    def size(self):
        return self.count


class station:
    def __init__(self,host,port):
        self.stations_ts = {}
        self.stations_username = {}
        self.stations_role = {}
        self.stations_device_type = {}
        self.stations_ip_address = {}
        self.stations_bssid = {}
        self.count = 0
        
        (station_result,error) = retrieveDataFromALE('station',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)
        
        self.count = len(station_result)

        for i,msg in enumerate(station_result):
            msg_content = msg['msg']
            ts = msg.get('ts',None)

            sta_eth_mac = msg_content['sta_eth_mac']
            sta_mac_addr = sta_eth_mac.get('addr', None)
            mac_custom.word_fmt = '%.2x'
            mac = str(EUI(sta_mac_addr, dialect=mac_custom))

            username = msg_content.get('username', None)
            if username == None:
                username = ''
            role = msg_content.get('role', None)
            if role == None:
                role = ''
            bssid_struct = msg_content.get('bssid', None)
            if bssid_struct:
                bssid = EUI(bssid_struct.get('addr', None), dialect=mac_custom)
            else:
                bssid = ''
            device_type = msg_content.get('device_type', None)
            if device_type == None:
                device_type == ''
            ip_address = msg_content.get('sta_ip_address')
            if ip_address:
                sta_ip_address = ip_address.get('addr')
            else:
                sta_ip_address = ''
            self.stations_ts[mac] = ts
            self.stations_username[mac] = username.encode('ascii', 'replace')
            self.stations_role[mac] = role
            self.stations_bssid[mac] = bssid
            self.stations_device_type[mac] = device_type
            self.stations_ip_address[mac] = sta_ip_address

    def __str__(self):  
        all_sta_str = "Number of Stations: %d\n" % self.count
        if self.count >= 1:
            all_sta_str = all_sta_str + "sta_mac         \tusername\trole\tip_address\tdevice_type\tbssid\n"
            for mac in sorted(self.stations_role.iterkeys()):
                sta_str = "%s\t%s\t%s\t%s\t%s\t%s\n" % (mac,self.stations_username[mac],
                    self.stations_role[mac],self.stations_ip_address[mac],self.stations_device_type[mac],
                    self.stations_bssid[mac])
                all_sta_str = all_sta_str + sta_str
        return all_sta_str

    def size(self):
        return self.count

    if storeInDB:
        def updateDB(self,conn):
            cursor = conn.cursor()

            for mac in self.stations_username:

                ale_dbi.upsert(cursor, 'Endpoint', ('macAddress',), schema=None, macAddress=mac,role=self.stations_role[mac])

                params = (mac,)            
                cursor.execute("SELECT id FROM Endpoint WHERE macAddress = %s", params)
                row = cursor.fetchone()
                if row == None:
                    print "station.updateDB(): Error in DB"
                else:
                    endpoint_id = row[0]

                username = self.stations_username[mac]
                role = self.stations_role[mac]
                devType = self.stations_device_type[mac]
                ip = self.stations_ip_address[mac]
                bssid = "%s" % self.stations_bssid[mac]

                params = ('restapi',username,role,ip,devType,bssid,endpoint_id)
                cursor.execute("UPDATE Endpoint SET lastHeardMessage=%s,username=%s,role=%s,ip=%s,devType=%s,bssid=%s WHERE id=%s",params)
            conn.commit()

"""
{"Station_result": [{"msg": {"sta_eth_mac": {"addr": "E4CE8F02CAB0"},"username": "ctang","role": "authenticated","bssid": {"addr": "6CF37FE71F71"},"device_type": "OS X","sta_ip_address": {"af": "ADDR_FAMILY_INET","addr": "172.18.164.161"},"hashed_sta_eth_mac": "2EA4E4206DA845A943E6D54E65B52BE0CD1DAA54","hashed_sta_ip_address": "43ED8A7F941EBB5998CE8837501B0BB6236A94E2"},"ts": 1383906326},{"msg": {"sta_eth_mac": {"addr": "8C2DAA682987"},"username": "ctang","role": "authenticated","bssid": {"addr": "6CF37FE71F71"},"device_type": "iPod","sta_ip_address": {"af": "ADDR_FAMILY_INET","addr": "172.18.164.157"},"hashed_sta_eth_mac": "B1B8814527641B97782F37702A06B40755769B67","hashed_sta_ip_address": "43ED8A7F941EBB5998CE8837501B0BB6236A94E2"},"ts": 1383787224}]}
"""

class application:
    """This class retrieve all the applications from ALE"""
    def __init__(self,host,port):
        self.applications = {}
        self.count = 0

        (application_result,error) = retrieveDataFromALE('application',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(application_result)

        for i,msg in enumerate(application_result):
            msg_content = msg['msg']
            app_id = int(msg_content['app_id'])
            app_name = msg_content['app_name']
            self.applications[app_id] = app_name

    def __str__(self):  
        all_application_str = "Items in application class: %d\n" % self.count
        if self.count >= 1:
            all_application_str = all_application_str + "Application ID\tApplication Name\n" 
            for app_id in sorted(self.applications.iterkeys()):
                application_str = "%s\t%s\n" % (app_id,self.applications[app_id])
                all_application_str = all_application_str + application_str
        return all_application_str

    def size(self):
        """Rerutn the number applications read"""
        return self.count

class destination:
    """This class retrieve all the destinationes from ALE"""
    def __init__(self,host,port):
        # Key is the IP address
        self.destinations = {}
        self.destinations_alias = {}
        self.count = 0
        
        (destination_result,error) = retrieveDataFromALE('destination',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(destination_result)

        for i,msg in enumerate(destination_result):
            msg_content = msg['msg']
            dest_ip_str = msg_content.get('dest_ip', None)
            dest_ip = str(dest_ip_str.get('addr',None))
            dest_name  = msg_content['dest_name']
            self.destinations[dest_ip] = dest_name
            alias_name = msg_content.get('dest_alias_name', None)
            if alias_name:
                self.destinations_alias[dest_ip] = alias_name

    def __str__(self):  
        all_destination_str = "Items in destination class: %d\n" % self.count
        if self.count >= 1:
            all_destination_str = all_destination_str + "Destination IP\tDestination Name\tDestination Alias\n"
            for dest_ip in sorted(self.destinations.iterkeys()):
                dest_alias_name = self.destinations_alias.get(dest_ip, None)
                if dest_alias_name == None:
                    dest_alias_name = ''
                dest_name = self.destinations.get(dest_ip, None)
                if dest_name == None:
                    dest_name = ''
                destination_str = "%s\t%s\t%s\n" %(dest_ip,dest_name,dest_alias_name)
                all_destination_str = all_destination_str + destination_str
        return all_destination_str

    def size(self):
        """Rerutn the number destinations read"""
        return self.count

"""
{"Destination_result": [
{"msg": 
    {
        "dest_ip": {
        "af": "ADDR_FAMILY_INET",
        "addr": "98.139.115.211"
        },
        "dest_name": "ci.beap.ad.yieldmanager.net",
        "dest_alias_name": "ad networks"}
    },
{"msg": {"dest_ip": {"af": "ADDR_FAMILY_INET","addr": "98.139.112.123"},"dest_name": "socialprofiles.zenfs.com"}}}
"""

class virtual_access_point:
    def __init__(self,host,port):
        # Dictionaries with bssid as keys
        self.radio_bssid = {}
        self.ssid = {}
        self.ts = {}
        self.count = 0
        
        (virtual_access_point_result, error) = retrieveDataFromALE('virtual_access_point',host,port)
        if error:
            print "Error retrieving data from REST: (%s)" % (error)

        self.count = len(virtual_access_point_result)

        for i,msg in enumerate(virtual_access_point_result):
            msg_content = msg['msg']
            ts = msg.get('ts',None)
            vap_bssid = msg_content['bssid']
            vap_radio_bssid = msg_content['radio_bssid']
            ssid = msg_content['ssid']

            bssid = str(convert_mac_fmt(vap_bssid))
            radio_bssid = str(convert_mac_fmt(vap_radio_bssid))

            self.radio_bssid[bssid] = radio_bssid
            self.ssid[bssid] = ssid
            self.ts[bssid] = ts

    def __str__(self):  
        all_virtual_access_point_str = "Number of VAP: %d\n" % self.count
        if self.count >= 1:
            all_virtual_access_point_str = all_virtual_access_point_str + "bssid\tradio_bssid\tssid\n"
            for bssid in sorted(self.radio_bssid.iterkeys()):
                bssid_str = "%s\t%s\t%s\n" % (bssid,self.radio_bssid[bssid],self.ssid[bssid])
                all_virtual_access_point_str = all_virtual_access_point_str + bssid_str
        return all_virtual_access_point_str

    if storeInDB:
        def updateDB(self,conn):
            cursor = conn.cursor()
    
            for bssid in self.radio_bssid:

                ale_dbi.upsert(cursor, 'VAP', ('bssid',), schema=None, bssid=bssid,essid=self.ssid[bssid])

                params = (bssid,)
                cursor.execute("SELECT id FROM VAP WHERE bssid = %s", params)
                row = cursor.fetchone()
                if row == None:
                    print "VAP.updateDB(): Error in DB"
                else:
                    vap_id = row[0]

                radio_bssid = self.radio_bssid[bssid]
                essid = self.ssid[bssid]
                ts = self.ts[bssid]

                radio_id = ale_dbi.getRadioIdByMac(conn,radio_bssid)

                params = (essid,radio_id,vap_id)
                cursor.execute("UPDATE VAP SET essid=%s,radio_id=%s WHERE id=%s",params)
            conn.commit()

    def size(self):
        """Rerutn the number destinations read"""
        return self.count
        
class proximity:
    pass

class presence:
    pass
        
class mac_custom(mac_unix): 
    pass

    
# if it is run from terminal:true, if it is imported :false
if __name__ == "__main__":
    if storeInDB:
        (conn,cursor) = ale_dbi.initDBConnection()
        server_id = ale_dbi.getServerID(conn,ale_host)

    c = campus(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved Campus IDs (%d)" % c.size()
    if verbose >= 2: print c
    if storeInDB:
        c.updateDB(conn,server_id)        

    b = building(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved Building IDs (%d)" % b.size()
    if verbose >= 2: print b
    if storeInDB:
        b.updateDB(conn,server_id)        

    f = floor(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved Floor IDs (%d)" % f.size()
    if verbose >= 2: print f
    if storeInDB:
        f.updateDB(conn,server_id)    

    a = access_point(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of access points (%d)" % a.size()
    if verbose >= 2: print a
    if storeInDB:
        a.updateDB(conn,server_id)

    r = radio(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of radios (%d)" % r.size()
    if verbose >= 2: print r
    if storeInDB:
        r.updateDB(conn)

    v = virtual_access_point(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of VAP (%d)" % v.size()
    if verbose >= 2: print v
    if storeInDB:
        v.updateDB(conn)

    s = station(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of associated stations (%d)" % s.size()
    if verbose >= 2: print s    
    if storeInDB:
        s.updateDB(conn)
    
    a = application(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of applications (%d)" % a.size()
    if verbose >= 2: print a    

    d = destination(ale_host,ale_restapi_port)
    if verbose >= 1: print "Retrieved list of destinations (%d)" % d.size()
    if verbose >= 2: print d    
    
    
    

