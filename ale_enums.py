#!/usr/bin/env python

# ale_enums.py

# This file stores the 'String' values of the enums used in protobuf.  
# Useful for easier output for reading

#
# Ideally, this file should be generated directly from schema.proto.
#

data_prio = [
    "DATA_PRIO_BK",                # Back
    "DATA_PRIO_BE",                # Best
    "DATA_PRIO_VI",                # Vide
    "DATA_PRIO_VO"                # Voic
]

# Traffic type
traffic_type = [
    "DATA_TRAFFIC_TYPE_BCAST",     # Broa
    "DATA_TRAFFIC_TYPE_MCAST",     # Mult
    "DATA_TRAFFIC_TYPE_UCAST"      # Unic
]

# HT Mode

ht_type = [
    "HTT_NONE",
    "HTT_20MZ",
    "HTT_40MZ",
    "HTT_VHT_20MZ",
    "HTT_VHT_40MZ",
    "HTT_VHT_80MZ",
]

# Phy Type

phy_type = [
    "PHY_TYPE_80211B",
    "PHY_TYPE_80211A",
    "PHY_TYPE_80211G"
]

network_type = [
    "INFRASTRUCTURE",
    "ADHOC"
]

util_stat_type = [
    "UTIL_STAT_TYPE_CHANNEL",
    "UTIL_STAT_TYPE_CHANNEL_TX",
    "UTIL_STAT_TYPE_CHANNEL_RX",
    "UTIL_STAT_TYPE_QUEUE_SWTX",
    "UTIL_STAT_TYPE_QUEUE_BE",
    "UTIL_STAT_TYPE_QUEUE_BK",
    "UTIL_STAT_TYPE_QUEUE_VI",
    "UTIL_STAT_TYPE_QUEUE_VO",
    "UTIL_STAT_TYPE_QUEUE_BCMC",
    "UTIL_STAT_TYPE_QUEUE_ATIM"
]

algorithm = [
    "ALGORITHM_TRIANGULATION",
    "ALGORITHM_AP_PLACEMENT",
    "ALGORITHM_CALIBRATION",
    "ALGORITHM_ESTIMATION",
    "ALGORITHM_LOW_DENSITY"
]

deployment_mode = [
    "DEPLOYMENT_MODE_CAMPUS",
    "DEPLOYMENT_MODE_REMOTE"
]

radio_mode = [
    "RADIO_MODE_AP",
    "RADIO_MODE_MESH_PORTAL",
    "RADIO_MODE_MESH_POINT",
    "RADIO_MODE_AIR_MONITOR",
    "RADIO_MODE_SPECTRUM_SENSOR",
    "RADIO_MODE_UNKNOWN"
]

security_msg_type = [
    "AUTH_SRVR_TIMEOUT_MSG",
    "MACAUTH_MSG",
    "CAPTIVE_PORTAL_MSG",
    "WPA_KEY_HANDSHAKE_MSG",
    "DOT1X_MSG",
    "UNKNOWN_MSG"
]

mode_type = [
    "CONTEXT",
    "CONTEXT_AND_LOCATION_WITH_CALIBRATION",
    "CONTEXT_AND_ESTIMATED_LOCATION"
]


measurement_unit = [
     "METERS",
     "FEET",
     "PIXELS"
]

if __name__ == "__main__":
    ht_type_str = "HTT_VHT_80MZ"
    radio_ht_type = ht_type.index("HTT_VHT_80MZ")

    print(radio_ht_type)

    rht = ht_type[4]

    print(rht)

