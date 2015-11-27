#!/usr/bin/env python

# ale_pprint.py

# Author: Albert Pang
# Created: November 16, 2015

# Functions for printing out an Protobuf encoded ALE message as JSON objects

import schema_pb2 as loco_pb2
import google.protobuf
import json
import re

debug = False

encoded_fields = [ 'hashed_sta_eth_mac', 'hashed_sta_ip_address', 'hashed_sta_mac', 'campus_id','building_id', 'floor_id', 
                    'webcc_md5', 'cc_md5', 'source_id', 'geofence_id', 'hashed_client_ip', 'hashed_device_mac',  ]
ip_addr_fields = [ 'client_ip', 'dest_ip', 'sta_ip_address']

complex_topics = [ ]

#
def convert_mac_fmt(bin_mac_addr):
    mac = str(":".join("%02x" % ord(a) for a in bin_mac_addr))
    return(mac)

def convert_ip_fmt(bin_ip_addr):
    ip = str(".".join("%d" % ord(a) for a in bin_ip_addr))
    return(ip)
    
def printTab(level):
    if level >= 1:
        print "\t" * (level),
    
def msgToJSON(msg,level=1,topic="",parentAddressIsIP=False):
    """
    returns a JSON object for a protobuf message
    """
    
    ap_rssi_p = re.compile('ap_rssi/(.*)')
    sta_rssi_p = re.compile('sta_rssi/(.*)')
    location_p = re.compile('location/(.*)')
    
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
    
    if debug: print "=>level=%d" % (level,)
    try: 
        fields = msg.ListFields()
        num_fields = len(fields)
    except AttributeError:
        fields = []
        num_fields = 0

    if debug:
        print "==>level=%d, num_fields=%d" % (level,num_fields)
        
    if num_fields == 0:
        return ""
#    printTab(level)

    output_str = "{"
    if level == 1 and topic != "":
        output_str = output_str + '\t"messageType" : "%s",' % (short_topic,)

    for field in fields:
        name = field[0].name
        addressIsIP = False
        if name in ip_addr_fields:
            addressIsIP = True
#        printTab(level)
        output_str = output_str + '"'+field[0].name+'":'
        attribute =  getattr(msg,name)
        next_level_output_str = msgToJSON(attribute,level+1,parentAddressIsIP=addressIsIP)
        output_str = output_str + next_level_output_str
        if next_level_output_str == "":
            if name == 'addr' and parentAddressIsIP:
                value = '"'+convert_ip_fmt(field[1])+'"'
            elif name == 'addr' or name == 'mac_address': 
                value = '"'+convert_mac_fmt(field[1])+'"'
#            elif name == 'hashed_sta_eth_mac' or name == 'hashed_sta_ip_address' or name == 'hashed_sta_mac' or name == 'campus_id' or name == 'building_id' or \
#                name == 'floor_id' or name == 'source_id':
            elif name in encoded_fields:
                value= '"'+field[1].encode("hex").upper()+'"'
            elif type(field[1]) is str or type(field[1]) is unicode:
                value = '"'+field[1]+'"'
            else:
                value = field[1]

            if type(value) is bool: # JSON doesn't like True/False
                if value:
                    value = 1
                else:
                    value = 0

            if type(value) is google.protobuf.internal.containers.RepeatedCompositeFieldContainer: # if it's a repeated field
                output_str = output_str + '['
                # printTab(level-1)
                num_items = len(value)
                i = 0
                for item in value:
                    output_str = output_str + msgToJSON(item,level+1)
                    # printTab(level)
                    i = i+1
                    if i < num_items:
                        output_str = output_str + ','
                output_str = output_str + ']'
            elif type(field[1]) is google.protobuf.internal.containers.RepeatedScalarFieldContainer: # if it's a list of values
                output_str = output_str + '['
                num_in_list = len(field[1])
                for f in field[1]:
                    output_str = output_str + '"'+f.encode("hex").upper()+'"'
                output_str = output_str + ']'
            else:
                output_str = output_str + str(value)
        
        num_fields = num_fields-1
        if num_fields > 0:
            if debug:
                output_str = output_str + ", (%d)" % (num_fields,)
            else:
                try:
                    output_str = output_str + ","
                except TypeError:
                    print type(output_str)
                    print output_str

    if debug:
        output_str = output_str + "} (%d)" % (num_fields,)
    else:
        output_str = output_str + "}"

    try:
        jo = json.loads(output_str)
    except ValueError:
        print "=============>ValueError====="
        print output_str
        print "============================="

    output_str = json.dumps(jo,indent=4)
    return (output_str)
