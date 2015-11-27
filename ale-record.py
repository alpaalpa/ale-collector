#!/usr/bin/env python

"""

Usage: 
    ale-record.py -u <URL> -w <out_filename> [ -t <topic1> ] [ -t <topic2>] ...

Simple script to subscribe to a ZMQ feed encoded in protobuf and record in a binary file.

Since ZMQ messages are not self-limiting, when saving a message, we preceed the message with
a message length (4 bytes).  

Also, protobuf messages are not self-identifying, for every message, ALE sends out two message,
first is the type of message (e.g. 'location', 'presence', etc), then the message itself.

Useful for reading and storing ALE feeds from a live system and then
playback for analysis.  Should work with both ALE 1.x and ALE 2.x
    
Examples:

        ale-record.py -u tcp://<serverip>:7779/ -w binary_file.ale
        ale-record.py -u tcp://<serverip>:7779/ -t location -w binary_file.ale

   for ALE 2.x, 7778 and 7777 are also used:        
        ale-record.py -u tcp://<serverip>:7778/ -t location

Author: Albert Pang
Based on work by: Roger Michaud
Date: October 2015
    Feb 2013 (original)

"""

verbose = 3

import google.protobuf as pb
import ale_pprint
import zmq
import re
#import string
import schema_pb2 as loco_pb2
import sys,getopt
import struct

def usage():
    """
    Prints usage of this program
    """
    
    global progname
    print 'usage: '+progname+' [-t <topic1>] [-t <topic2>] ... -u <serverUrl> [-w <output_file>] -d'
    print '''
            -t <topic> e.g. 
                -t location 
                (multiple instances of -t can be specified)
                -t location -t proximity
            -u <serverurl> e.g.
                -u tcp://SERVERIP:7779/
            -w <filename>
                Output filename to store ALE streams
            -d  Dump message on screen
    '''
    sys.exit(2)

class Usage(Exception):
    """
    Exception class for this module. Used instead of sys.exit(n)
    """
    def __init__(self, msg = ""):
        self.msg = msg
    def __str__(self):
        return self.msg

#construction of the deviceLocation protobuf message to store the protobuf obj receive in the zmq msg
def dumpMessage(topic,data):
    global countEvent
    global verbose


    msg = loco_pb2.nb_event()
        
# Original code has the following.  But don't think it's needed.    
#   msg.Clear()
    msg.ParseFromString(data)
    msg_json = ale_pprint.msgToJSON(msg,level=1,topic=topic)

#    json_obj = protobuf_json.pb2json(msg)
#    print pprint.pprint(json_obj, depth = 4)    

    print msg_json

def main(argv):
    global progname
    global filename # output filename
    
    #global counters 
    global countEvent
    global verbose
    
    progname=argv[0]


    # Program Default Options
    verbose = 1
    dump_message = False
    write_file = False
    filename = "ale-dump.dat"

    # List of subscribed topics.  Can be multiple
    subscribed_topics = []
    
    #default url
    url = "tcp://localhost:7779"
    
    #parsing the command line arguments
    try:
      opts, args = getopt.getopt(argv[1:],"w:t:u:d")
      
      #in case of no arguments given or no option (no -)
      if (len(argv)==1 or not(argv[1].startswith('-'))): 
        raise getopt.GetoptError('',None)
    
    except getopt.GetoptError:
      usage()
    
    for o,a in opts:
        if o=='-t':
          topic = a
          print 'Subscribe to topic: '+topic
          subscribed_topics.append(topic)
        elif o=='-u':
          url = a
          print 'url of location Server: '+url
        elif o=='-w': 
            write_file = True
            filename = a
        elif o=='-d':
            dump_message = True
        else:
            usage()
            raise Usage("Could not parse argument: %s" % o)
              
    #core of main
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(url)
    if len(subscribed_topics):
        for topic in subscribed_topics:
            subscriber.setsockopt_string(zmq.SUBSCRIBE,unicode(topic)) #encoding string from unicod to utf-8
    else:
        print "Subscribe to all topics"
        subscriber.setsockopt_string(zmq.SUBSCRIBE,unicode('')) #encoding string from unicod to utf-8
    
    #forever loop to wait publish
    print 'waiting for zmq sub msg'
    print
    
    topic_dict = {}
    done = False
    countEvent = 0

    if write_file:
        try:
            binfile = open (filename, "wb")
        except IOError:
            print progname+": cannot open %s for writing. Exiting." % (filename,)
            sys.exit()

    long_topic_p = re.compile('^(ap_rssi|sta_rssi|location)/(.*)')
    
    while(True):
        try:
            #we know we will receive two messages topic (str) and data (protobuf string to parse)
            topic = subscriber.recv()
            if write_file:
                binfile.write(struct.pack("i", len(topic)))
                binfile.write(topic)
                
            match_long_topic = long_topic_p.match(topic)
            
            if match_long_topic:
                topic = match_long_topic.group(1)

            data = subscriber.recv()
            print "Topic: %-15s (%4d)" % (topic,len(data))

            if write_file:
                binfile.write(struct.pack("i", len(data)))
                binfile.write(data)

            if not topic_dict.has_key(topic):
                topic_dict[topic] = 1
            else:
                topic_dict[topic] += 1
            
            countEvent += 1
            if dump_message:
                dumpMessage(topic,data)

        except KeyboardInterrupt:
            print "client unsubscribed"
            done = 1
        
        if not verbose or done:
            keys = topic_dict.keys()
            keys.sort()
            print "Total %d topics" % len(keys)
            for k in keys:
                print "\t %-20s %d" % (k, topic_dict[k])
            print "Total events: %d" % (countEvent,)

        if done:
            sys.stderr.flush()
            if write_file:
                binfile.close()
            break

# if it is run from terminal:true, if it is imported :false
if __name__ == "__main__":
    main(sys.argv)
