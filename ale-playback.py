#!/usr/bin/env python


"""

ale-playback.py file

Reads a saved protobuf feed from ALE from a file for processing

"""

import os
import sys
import struct
#import protobuf_json
#import pprint
import ale_pprint
import schema_pb2 as loco_pb2

debug = 0

def usage():
    print sys.argv[0], " filename"

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    usage()
    exit()


def handleMsg(topic,data):
    # Since protobuf messages are not self-defining, easiest way is to use another field to 
    msg = loco_pb2.nb_event()
    msg.ParseFromString(data)

    msg_json = ale_pprint.msgToJSON(msg,topic=topic)

    print msg_json
    
#    json_obj = protobuf_json.pb2json(msg)
#    print pprint.pprint(json_obj, depth = 4)    

#------------------------------------------------------------------------------------

binfile = open (filename, "rb")
byteread = 0
filesize = os.path.getsize(filename)

while byteread < filesize:
    topic_len_bin = binfile.read(4)
    byteread += 4
    if topic_len_bin:
        (topic_length,) = struct.unpack("i",topic_len_bin)
    
        byteread += topic_length
    
        if topic_length > 0:
            topic = binfile.read(topic_length)
        
#            print '{\n\t"messageType" : "%s"\n}' % (topic,)
    
            data_len_bin = binfile.read(4)
            byteread += 4
            (data_length,) = struct.unpack("i",data_len_bin)
    
            if data_length > 0:
                data = binfile.read(data_length)
                handleMsg(topic,data)