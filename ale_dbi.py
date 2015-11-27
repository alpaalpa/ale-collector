#!/usr/bin/env python
# -*- codendpointing: utf-8 -*-

#
#ALETimestamp
# ale_dbi.py
#
#
# Handles all DBI functionality for the LBS system
#
#  Version: PostgreSQL

import sys
import psycopg2
import psycopg2.extras
import datetime,time

import config

typeToTable = {
    'campus': 'campus',
    'building': 'building',
    'floor': 'floor',
    'endpoint': 'endpoint'
}

typeID = {
    'campus': 0,
    'building': 1,
    'floor': 2,
    'server': 4
}


# A arbitrary id for campus_id, building_id, floor_id
very_large_id = 99999

def upsert(db_cur, table, pk_fields, schema=None, **kwargs):
    """Updates the specified relation with the key-value pairs in kwargs if a
    row matching the primary key value(s) already exists.  Otherwise, a new row
    is inserted.  Returns True if a new row was inserted.

    schema     the schema to use, if any (not sanitized)
    table      the table to use (not sanitized)
    pk_fields  tuple of field names which are part of the primary key
    kwargs     all key-value pairs which should be set in the row
    """
    assert len(pk_fields) > 0, "must be at least one field as a primary key"
    if schema:
        rel = '%s.%s' % (schema, table)
    else:
        rel = table
 
    # check to see if it already exists
    where = ' AND '.join('%s=%%s' % pkf for pkf in pk_fields)
    where_args = [kwargs[pkf] for pkf in pk_fields]
    db_cur.execute("SELECT COUNT(*) FROM %s WHERE %s LIMIT 1" % (rel, where), where_args)
    fields = [f for f in kwargs.keys()]
    if db_cur.fetchone()[0] > 0:
        set_clause = ', '.join('%s=%%s' % f for f in fields if f not in pk_fields)
        set_args = [kwargs[f] for f in fields if f not in pk_fields]
        db_cur.execute("UPDATE %s SET %s WHERE %s" % (rel, set_clause, where), set_args+where_args)
        return False
    else:
        field_placeholders = ['%s'] * len(fields)
        fmt_args = (rel, ','.join(fields), ','.join(field_placeholders))
        insert_args = [kwargs[f] for f in fields]
        db_cur.execute("INSERT INTO %s (%s) VALUES (%s)" % fmt_args, insert_args)
        return True

def logNotification(conn,endpoint_id,status_code,msg):
    params = (endpoint_id, status_code, msg)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notification (endpoint_id,sentStatus,message) VALUES (%s,%s,%s)", params)
    conn.commit()
    

def macAddressToEndpointID(conn,macaddress):
    params = (macaddress,)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM endpoint WHERE macAddress = %s', params)
    # Look-up endpoint from endpoint table based on mac address
    row = cursor.fetchone()
    if row == None:
        return 0
    else:
        return row[0]

def endpointIDToMacAddress(conn,endpoint_id):
    params = (endpoint_id,)
    cursor = conn.cursor()
    cursor.execute('SELECT macAddress FROM endpoint WHERE id = %s', params)
    row = cursor.fetchone()
    if row == None:
        return "xx:xx:xx:xx:xx:xx"
    else:
        return row[0]

def AWMSIDToDBID(conn,type,awms_id):
#    table = typeToTable[type]   # This doesn't work
    
    if config.verbose >=5:
        print "idFromAWMS = ", awms_id

    cursor = conn.cursor()
    params = (awms_id,)

    if type == 'campus':
        cursor.execute('SELECT id FROM Campus WHERE idFromAWMS = %s', params)
    elif type == 'building':
        cursor.execute('SELECT id FROM Building WHERE idFromAWMS = %s', params)
    elif type == 'floor':
        cursor.execute('SELECT id FROM Floor WHERE idFromAWMS = %s', params)
    else:
        print "AWMSIDToDBID(): Unknown Type Error"

    row = cursor.fetchone()
    if row == None:
        return 0
    else: 
        return row[0]    
    
def getNameFromDBID(conn,type,db_id):
    pass

def getCampusName(conn,campus_id):
    cursor = conn.cursor()
    params = (db_id,)
    cursor.execute("SELECT name FROM Campus WHERE id = %s", params)
    row = cursor.fetchone()
    if row == None:
        return 'Unknown'
    else:
        return row[0]
    if row == None:
        return 0
    else:
        return row[0]

def campusIDToDBID(conn,campus_id):
    return AWMSIDToDBID(conn,'campus',campus_id)

def buildingIDToDBID(conn,building_id):
    return AWMSIDToDBID(conn,'building',building_id)

def floorIDToDBID(conn,floor_id):
    return AWMSIDToDBID(conn,'floor',floor_id)
    
def getCampusIDList(conn,server_id=None):
    # If server_id == None, then return a list of all Campus ID
    cursor = conn.cursor()
    if server_id == None:
        cursor.execute("SELECT id FROM Campus ORDER BY id")
        rows = cursor.fetchall()
        return [i for i, in rows]
    else:
        params = (server_id,)
        cursor.execute("SELECT id FROM Campus WHERE server_id=%s ORDER BY id",params)
        rows = cursor.fetchall()
        return [i for i, in rows]

def getBuildingIDList(conn,campus_id=None):
    cursor = conn.cursor()
    if campus_id == None:
        cursor.execute("SELECT id FROM Building ORDER BY id")
        rows = cursor.fetchall()
        return [i for i, in rows]
    else:
        params = (campus_id,)
        cursor.execute("SELECT id FROM Building WHERE campus_id=%s ORDER BY id",params)
        rows = cursor.fetchall()
        return [i for i, in rows]
    
def getFloorIDList(conn,building_id=None):
    cursor = conn.cursor()
    if building_id == None:
        cursor.execute("SELECT id FROM Floor ORDER BY id")
        rows = cursor.fetchall()
        return [i for i, in rows]
    else:
        params = (building_id,)
        cursor.execute("SELECT id FROM Floor WHERE building_id=%s ORDER BY id",params)
        rows = cursor.fetchall()
        return [i for i, in rows]

def getLocationEndpointCount(conn,campus_id=None,building_id=None,floor_id=None,interval_start=None,interval=60*60):
    # Only one of server_id, campus_id, building_id, floor_id can be != None
    cursor = conn.cursor()
    if campus_id != None:
        if interval_start != None:
            interval_stop = interval_start + datetime.timedelta(seconds=interval)
            params = (interval_start,interval_stop,campus_id)
            cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM Location WHERE serverTimestamp >= %s AND serverTimestamp < %s AND campus_id=%s",params)
            row = cursor.fetchone()
            return row[0]
        else:
            params = (campus_id,)
            cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM Location WHERE campus_id=%s",params)
            row = cursor.fetchone()
            return row[0]
    if building_id != None:
        if interval_start != None:
            interval_stop = interval_start + datetime.timedelta(seconds=interval)
            params = (interval_start,interval_stop,building_id)
            cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM Location WHERE serverTimestamp >= %s AND serverTimestamp < %s AND building_id=%s",params)
            row = cursor.fetchone()
            return row[0]
        else:
            params = (building_id,)
            cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM Location WHERE building_id=%s",params)
            row = cursor.fetchone()
            return row[0]
    if floor_id != None:
        if interval_start != None:
            interval_stop = interval_start + datetime.timedelta(seconds=interval)
            params = (interval_start,interval_stop,floor_id)
            cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM Location WHERE serverTimestamp >= %s AND serverTimestamp < %s AND floor_id=%s",params)
            row = cursor.fetchone()
            return row[0]
        else:
            params = (floor_id,)
            cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM Location WHERE floor_id=%s",params)
            row = cursor.fetchone()
            return row[0]
    
def addEndpoint(conn,macaddr,method,isAssociated=None,rssi=None):
    cursor = conn.cursor()

    if rssi == None:
        params = (macaddr,method,isAssociated)
        cursor.execute('INSERT INTO Endpoint (macAddress,lastModifiedTime,lastHeardTime,lastHeardMessage,isAssociated) VALUES (%s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,%s,%s)', params)
    else:
        params = (macaddr,method,isAssociated,rssi)
        cursor.execute('INSERT INTO Endpoint (macAddress,lastModifiedTime,lastHeardTime,lastHeardMessage,isAssociated,maxRSSI) VALUES (?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,%s,%s,%s)', params)
        
    params = (macaddr,)
    cursor.execute('SELECT id FROM endpoint WHERE macAddress = %s', params)
    row = cursor.fetchone()
    if row == None:
        return 0
    else:
        return row[0]


def updateEndpoint(conn,endpoint_id,method,isAssociated=None,rssi=None):
    cursor = conn.cursor()


    if rssi == None:
        params = (method,endpoint_id,isAssociated)
        cursor.execute('UPDATE Endpoint SET lastModifiedTime=CURRENT_TIMESTAMP,lastHeardTime=CURRENT_TIMESTAMP, lastHeardMessage = %s, isAssociated = %s WHERE id = %s', params)
    else:
        params = (endpoint_id,)
        cursor.execute('SELECT * FROM endpoint WHERE id = %s', params)
        row = cursor.fetchone()
        maxRSSI = row['maxRSSI']
        if rssi >= maxRSSI: 
            maxRSSI = rssi
        params = (method,isAssociated,maxRSSI,endpoint_id)
        cursor.execute('''
            UPDATE Endpoint SET lastModifiedTime=CURRENT_TIMESTAMP,lastHeardTime=CURRENT_TIMESTAMP, 
                lastHeardMessage = %s, isAssociated = %s, maxRSSI = %s WHERE id = %s
        ''', params)
    conn.commit()

    return endpoint_id
    
# 

def updateEndpointByMac(conn,macaddr,method,isAssociated=None,rssi=None):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    upsert(cursor, 'Endpoint', ('macAddress',), schema=None, macAddress=macaddr, lastHeardMessage=method)

    endpoint_id = macAddressToEndpointID(conn,macaddr)

    if rssi == None:
        params = (method,isAssociated,endpoint_id)
        cursor.execute('UPDATE Endpoint SET lastModifiedTime=CURRENT_TIMESTAMP,lastHeardTime=CURRENT_TIMESTAMP, lastHeardMessage = %s, isAssociated = %s WHERE id = %s', params)
        conn.commit()
    else:
        params = (endpoint_id,)
        cursor.execute('SELECT maxRSSI FROM endpoint WHERE id = %s', params)
        row = cursor.fetchone()
        maxRSSI = row[0]
        if rssi >= maxRSSI: 
            maxRSSI = rssi
        params = (method,isAssociated,maxRSSI,endpoint_id)
        cursor.execute('''
            UPDATE Endpoint SET lastModifiedTime=CURRENT_TIMESTAMP,lastHeardTime=CURRENT_TIMESTAMP, 
                lastHeardMessage = %s, isAssociated = %s, maxRSSI = %s WHERE id = %s
        ''', params)

    conn.commit()

    return endpoint_id
    
def updateEndpointDetails(conn,endpoint_id,username,role,bssid,device_type,ip):
    cursor = conn.cursor()
    params = (username,role,bssid,device_type,ip,endpoint_id)
    cursor.execute("UPDATE Endpoint SET username=%s,role=%s,bssid=%s,devType=%s,ip=%s WHERE id=%s",params)
    conn.commit()
    
def addLocation(conn,endpoint_id,ale_ts,campus_id,building_id,floor_id,x,y,algorithm):
    params = (endpoint_id,ale_ts,campus_id,building_id,floor_id,int(x),int(y),algorithm)
    cursor = conn.cursor()
    # Handle error conditions
    if endpoint_id == 0:
        pass
    if campus_id == 0:
        pass
    if building_id == 0:
        pass
    if floor_id == 0:
        pass
        
    cursor.execute('''INSERT INTO Location 
        (endpoint_id,serverTimestamp,ALETimestamp,campus_id,building_id,floor_id,x,y,algorithm) 
        VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s,%s,%s,%s,%s)''', params)
    conn.commit()
    return 0
    
    
def addGeofenceNotify(conn,endpoint_id,ale_ts,geofence_name,ap_name,bssid,rssi):

    ap_id = getAPIdByName(conn,ap_name)
    params = (endpoint_id,ale_ts,geofence_name,ap_name,ap_id,bssid,rssi)    
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO Geofence_Notify 
        (endpoint_id,serverTimestamp,ALETimestamp,geofenceName,apName,ap_id,bssid,rssi)
        VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s,%s,%s,%s)''', params)
    conn.commit()
    return 0
    
def addRSSI(conn,endpoint_id,ale_ts,radio_id,rssi,isAssociated,age=None,noise_floor=None,assoc_bssid=None):
    params = (endpoint_id,ale_ts,radio_id,rssi,isAssociated,age,noise_floor,assoc_bssid)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO RSSI (endpoint_id,serverTimestamp,ALETimestamp,radio_id,rssi,isAssociated,age,noise_floor,assoc_bssid)
        VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s,%s,%s,%s,%s)
    ''',params)
    conn.commit()
    return 0

def addPresence(conn,endpoint_id,ale_ts,isAssociated,ap_name,radio_id,server_id,age=None,noise_floor=None,assoc_bssid=None,rssi=None):
    cursor = conn.cursor()
    if radio_id:
        params = (endpoint_id,ale_ts,isAssociated,ap_name,radio_id,server_id,rssi)
        cursor.execute('''INSERT INTO Presence (endpoint_id,serverTimestamp,ALETimestamp,isAssociated,ap_name,radio_id,server_id,rssi)
            VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s,%s,%s,%s)
            ''',params)
    else:
        params = (endpoint_id,ale_ts,isAssociated,ap_name,server_id,rssi)
        cursor.execute('''INSERT INTO Presence (endpoint_id,serverTimestamp,ALETimestamp,isAssociated,ap_name,server_id,rssi)
            VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s,%s,%s)
            ''',params)
    conn.commit()
    return 0
    
def getRadioIdByMac(conn,radio_mac):
    cursor = conn.cursor()
    if radio_mac == 0:
        radio_mac = "xx:xx:xx:xx:xx:xx"
    params = (radio_mac,)
    cursor.execute("SELECT id FROM Radio_BSSID WHERE radio_bssid=%s",params)
    row=cursor.fetchone()
    if row == None:
        return(0)
    else:
        return row[0]

def getAPIdByRadioMac(conn,radio_mac):
    cursor = conn.cursor()
    params = (radio_mac,)
    cursor.execute("SELECT ap_id FROM Radio_BSSID WHERE radio_bssid=%s",params)
    row=cursor.fetchone()
    if row == None:
        return(0)
    else:
        return row[0]  
        
def getAPIdByName(conn,name):
    cursor = conn.cursor()
    params = (name,)
    cursor.execute("SELECT id FROM AP WHERE name=%s",params)
    row=cursor.fetchone()
    if row == None:
        return(0)
    else:
        return row[0]      

def getAPIdByMac(conn,wired_mac):
    cursor = conn.cursor()
    params = (wired_mac,)
    cursor.execute("SELECT id FROM AP WHERE macAddress=%s",params)
    row=cursor.fetchone()
    if row == None:
        return updateAP(conn,ap_eth_mac=wired_mac)
    else:
        return row[0]

def getAPNameById(conn,ap_id):
    cursor = conn.cursor()
    params = (ap_id,)
    cursor.execute("SELECT macAddress,name FROM AP WHERE id=%s",params)
    row=cursor.fetchone()
    if row == None:
        return(0,'')
    else:
        return row[0],row[1]

def getFirstameByEndpointID(conn,endpoint_id):
    firstname = None
    language = config.defaultLanguage

    cursor = conn.cursor()
    params = (endpoint_id,)
    cursor.execute("""
    SELECT p.firstname, p.country, p.language FROM endpoint_Person ep
    	LEFT OUTER JOIN Endpoint e
    	ON ep.endpoint_id = e.id
    	LEFT OUTER JOIN Person p
    	ON ep.person_id = p.id
    	WHERE e.id = %s;
    """,params)

    row = cursor.fetchone()
    if row == None:
        return(firstname, language)
    else:
        if config.verbose >= 3: print "Row:", row
        firstname = row[0]
        country = str(row[1])
        language = str(row[2])
        if config.verbose >= 3: print "In getFirstnameByEndpointID: Firstname: [%s] Country: [%s] Language is: [%s]" % (firstname,country,language)
        if language == None:
            language = config.countryToLanguage.get(country, config.defaultLanguage)
        return(firstname, language)

def updateCampus(conn,campus_awms_id,campus_name,server_id):

    cursor = conn.cursor()

    upsert(cursor, 'Campus', ('idFromAWMS',), schema=None, idFromAWMS=campus_awms_id, name=campus_name)

    params = (campus_awms_id,)
    cursor.execute("SELECT id FROM Campus WHERE idFromAWMS = %s", params)
    row = cursor.fetchone()
    if row == None:
        campus_id = 0
        print "ERROR INSERTING INTO DB"
        return 0
    else:
        campus_id = row[0]
    params = (campus_name,server_id,campus_id)
    cursor.execute("UPDATE Campus SET lastModifiedTime = CURRENT_TIMESTAMP, name = %s, server_id=%s WHERE id = %s", params)
    conn.commit()
    return campus_id
    
def updateBuilding(conn,building_awms_id,building_name,campus_id):
    cursor = conn.cursor()
    
    upsert(cursor, 'Building', ('idFromAWMS',), schema=None, idFromAWMS=building_awms_id, name=building_name)
    
    params = (building_awms_id,)
    cursor.execute("SELECT id FROM Building WHERE idFromAWMS = %s", params)
    row = cursor.fetchone()
    if row == None:
        building_id = 0
        print "ERROR INSERTING INTO DB"
        return 0
    else:
        building_id = row[0]
    params = (building_name,campus_id,building_id)
    cursor.execute("UPDATE Building SET lastModifiedTime = CURRENT_TIMESTAMP, name = %s, campus_id = %s WHERE id = %s", params)
    conn.commit()
    return building_id

def updateFloor(conn,floor_awms_id,floor_name,latitude,longitude,img_path,img_width,img_length,building_id,level,units,grid_size):
    cursor = conn.cursor()
    
    upsert(cursor, 'Floor', ('idFromAWMS',), schema=None, idFromAWMS=floor_awms_id, name=floor_name)

    params = (floor_awms_id,)
    cursor.execute("SELECT id FROM Floor WHERE idFromAWMS = %s", params)
    row = cursor.fetchone()
    if row == None:
        floor_id = 0
        print "ERROR INSERTING INTO DB"
        return 0
    else:
        floor_id = row[0]

    params = (floor_name,latitude,longitude,img_path,img_width,img_length,building_id,level,units,grid_size,floor_id)
    cursor.execute("UPDATE Floor SET lastModifiedTime = CURRENT_TIMESTAMP,name=%s,latitude=%s,longitude=%s,img_path=%s,img_width=%s,img_length=%s,building_id=%s,level=%s,units=%s,grid_size=%s WHERE id = %s", params)
    conn.commit()
    return floor_id
    
def updateAP(conn,ap_eth_mac="ff:ff:ff:ff:ff:ff",name=None,group=None,model=None,mode=None,ip=None,reboots=None,rebootstraps=None,server_id=None):
    cursor = conn.cursor()
    upsert(cursor, 'AP', ('macAddress',), schema=None, macAddress=ap_eth_mac,name=name)

    params = (ap_eth_mac,)
    cursor.execute("SELECT id FROM AP WHERE macAddress = %s", params)
    row = cursor.fetchone()
    if row == None:
        print "access_point.updateDB(): Error in DB"
    else:
        ap_id = row[0]

    params = (ap_id,)
    cursor.execute("UPDATE AP SET lastmodifiedtime = CURRENT_TIMESTAMP WHERE id = %s", params)

    if name:
        params = (name,ap_id)
        cursor.execute("UPDATE AP SET name=%s WHERE id = %s", params)
    if group:
        params = (group,ap_id)
        cursor.execute("UPDATE AP SET apGroup=%s WHERE id = %s", params)
    if model:
        params = (model,ap_id)
        cursor.execute("UPDATE AP SET model=%s WHERE id = %s", params)
    if mode:
        params = (mode,ap_id)
        cursor.execute("UPDATE AP SET mode=%s WHERE id = %s", params)
    if ip:
        params = (ip,ap_id)
        cursor.execute("UPDATE AP SET ip=%s WHERE id = %s", params)
    if reboots:
        params = (reboots,ap_id)
        cursor.execute("UPDATE AP SET reboots=%s WHERE id = %s", params)
    if rebootstraps:
        params = (rebootstraps,ap_id)
        cursor.execute("UPDATE AP SET rebootstraps=%s WHERE id = %s", params)
    if server_id:
        params = (server_id,ap_id)
        cursor.execute("UPDATE AP SET server_id=%s WHERE id = %s", params)
    conn.commit()
    return ap_id

def updateRadio(conn,ap_id,radio_bssid,mode,phy,ht):
    cursor = conn.cursor()
    upsert(cursor, 'Radio_BSSID', ('radio_bssid',), schema=None, radio_bssid=radio_bssid,ap_id=ap_id)

    params = (radio_bssid,)
    cursor.execute("SELECT id FROM Radio_BSSID WHERE radio_bssid = %s", params)
    row = cursor.fetchone()
    if row == None:
        print "radio.updateDB(): Error in DB"
    else:
        radio_id = row[0]

    params = (radio_id,)
    cursor.execute("UPDATE Radio_BSSID SET lastmodifiedtime = CURRENT_TIMESTAMP WHERE id = %s", params)

    if phy is not None:
        params = (phy,radio_id)
        cursor.execute("UPDATE Radio_BSSID SET phyType=%s WHERE id = %s", params)
    if ht is not None:
        params = (ht,radio_id)
        cursor.execute("UPDATE Radio_BSSID SET ht=%s WHERE id = %s", params)

    if mode is not None:
        params = (mode,radio_id)
        cursor.execute("UPDATE Radio_BSSID SET mode=%s WHERE id = %s", params)

    conn.commit()
    return radio_id

def updateVAP(conn,radio_id,bssid,essid):
    cursor = conn.cursor()
    upsert(cursor, 'VAP', ('bssid',), schema=None, bssid=bssid,radio_id=radio_id)

    params = (bssid,)
    cursor.execute("SELECT id FROM VAP WHERE bssid = %s", params)
    row = cursor.fetchone()
    if row == None:
        print "vap.updateDB(): Error in DB"
    else:
        vap_id = row[0]

    params = (vap_id,)
    cursor.execute("UPDATE VAP SET lastmodifiedtime = CURRENT_TIMESTAMP WHERE id = %s", params)

    if essid:
        params = (essid,vap_id)
        cursor.execute("UPDATE VAP SET essid=%s WHERE id = %s", params)

    conn.commit()
    return vap_id

def initDBConnection():
    connect_str = "dbname='%s' user='%s' host='%s' password='%s'" % (config.db_name, config.db_userid, 
                                                                     config.db_host, config.db_password)

    conn = psycopg2.connect(connect_str)    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    params = ('table', 'Endpoint')
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type=%s AND name=%s", params)
    row = cursor.fetchone()
    if row == None:
        # Need to throw an exception and exit
        raise Exception("SQL DB '%s' not properly initialized.\n\tInitialize with: sqlite3 -init ale.sql %s" % (config.db_file,config.db_file))
    """ 
    cursor.execute("SET TIMEZONE = 'UTC'")
    return (conn,cursor)
    
def getServerID(conn,host):
    cursor = conn.cursor()
    upsert(cursor, 'Server', ('host',), schema=None, host=host,name=host)
    params = (host,)
    cursor.execute("SELECT id FROM Server WHERE host=%s", params)
    row = cursor.fetchone()
    server_id = 0
    if row == None:
        print "getServerID(): Error in DB"
    else:
        server_id = row[0]

    conn.commit()
    return server_id

def getUnkwownCampusID(conn):
    pass

def getUnknownBuildingID(conn):
    pass
    
def getUnknownFloorID(conn):
    pass

def getUnknownAPID(conn):
    pass

# if it is run from terminal:true, if it is imported :false
if __name__ == "__main__":
    (conn,cursor) = initDBConnection()
    
    """
    endpoint_id = macAddressToEndpointID(conn,'e0:9d:31:1d:5d:a8')

    macAddr = endpointIDToMacAddress(conn,endpoint_id)
    print endpoint_id, macAddr
    
    updateCampus(conn,'CAMPUSID1','CAMPUSNAME  1')
    """
    
    print getCampusIDList(conn)
    print getCampusIDList(conn,1)
    print getCampusIDList(conn,2)

    print getBuildingIDList(conn)
    print getBuildingIDList(conn,1)
    
    print getFloorIDList(conn)
    
    print getAPIdByMac(conn,"xx:xx:xx:xx:xx:xx")
    
    
