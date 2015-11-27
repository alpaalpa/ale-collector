#!/usr/bin/env python

import re
import urllib

# An updated version of oui.txt can be found at:
# http://standards-oui.ieee.org/oui.txt

OUI_FILE = "oui.txt"
global oui
oui = {}

debug = False

def initializeOUITable():
    global oui
    if debug: print "Parsing data..."
    with open(OUI_FILE) as infile:
        for line in infile:
            #do_something_with(line)
            if re.search("(hex)", line):
                try:
                    mac,vendor = line.strip().split("(hex)")
                except:
                    mac = vendor = ''
    #            print line.strip().split("(hex)")
                mac = mac.strip().replace("-",":").lower()
                vendor = vendor.strip()
                if debug:
                    print "[%s][%s]" % (mac,vendor)
                oui[mac] = vendor

def getOUI(mac_addr):
    """
    Get the OUI portion of an Mac Address and return the OUI component in xx:xx:xx format
    """
    mac_format1 = re.compile('([\da-fA-F][\da-fA-F][:-][\da-fA-F][\da-fA-F][:-][\da-fA-F][\da-fA-F])[:-]([\da-fA-F][\da-fA-F][:-][\da-fA-F][\da-fA-F][:-][\da-fA-F][\da-fA-F])')
    mac_format2 = re.compile('([a-fA-F][a-fA-F][a-fA-F][a-fA-F][a-fA-F][a-fA-F])([a-fA-F][a-fA-F][a-fA-F][a-fA-F][a-fA-F][a-fA-F])')

    m = mac_format1.match(mac_addr)
    if m:
        mac_oui = m.group(1)
        mac_oui = mac_oui.strip().replace("-",":").lower()
        return mac_oui
        
def getVendor(mac_addr):
    return oui.get(getOUI(mac_addr),None)

if __name__ == "__main__":
    initializeOUITable()
    mac_addr = '80:e6:50:0e:eb:a2'
    print getOUI('80:e6:50:0e:eb:a2'),oui[getOUI('80:e6:50:0e:eb:a2')],getVendor(mac_addr)