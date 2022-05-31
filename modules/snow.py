"""
This module will allow you to collect ServiceNow location for the devices in IP Fabric

Required variables:
    sNowServer: (str) IP Address or the DNS name of ServiceNow
    sNowUser: (str) username for ServiceNow
    sNowPass: (str) password for this user
    ipfDevs: (list of dict) of all devices in IP Fabric, only hostname is required
        [
            {'hostname': 'xx', 'siteName': 'xx', 'loginIp': '10.0.0.1'},
            {'hostname': 'yy', 'siteName': 'yy', 'loginIp': '10.0.0.1'}
        ]

Returns a list of dict:
        [
            {'hostname': 'xx', 'location': 'SNOW-location-xx'},
            {'hostname': 'yy', 'location': 'SNOW-location-yy'},
        ]
"""

import httpx
from rich import print

SNOW_HEADERS = {
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def fetchLocationName(sNowDevice, sNowLocations):
    
    location_name = "Location Not Set in SNOW"
    try:
        device_loc_raw = dict(sNowDevice["location"])
        for location in sNowLocations:
            device_loc_id = device_loc_raw.get("value", "")
            if location["sys_id"] == device_loc_id:
                location_name = location["name"]
    except Exception as exc:
        location_name = "ERR - Not in SNOW"
    return location_name

def fetchSNowDevicesLoc(sNowServer, sNowUser, sNowPass, ipfDevs):
    """
    Function to collect data from SNow and return the JSON containing hostname and site location
    """
    devices_loc = []
    
    devicesEndpoint = (
        "https://" + sNowServer + "/api/now/table/cmdb_ci_netgear"
    )
    locationsEndpoint = (
        "https://" + sNowServer + "/api/now/table/cmn_location"
    )
    try:
        sNowDevices_raw = httpx.get(
            devicesEndpoint, auth=(sNowUser, sNowPass), headers=SNOW_HEADERS, timeout=120
        )
        sNowDevices = sNowDevices_raw.json()["result"]
        sNowLocations_raw = httpx.get(
            locationsEndpoint, auth=(sNowUser, sNowPass), headers=SNOW_HEADERS, timeout=120
        )
        sNowLocations = sNowLocations_raw.json()["result"]
        print(f"##INFO## {len(sNowDevices)} devices found in ServiceNow")
    except Exception as exc:
        print(f"##WARNING## Type of error: {type(exc)}")
        print(f"##WARNING## Message: {exc.args}")
        print("##WARNING## Can't process SNow data (server hibernation...)")

    print(f"##INFO## Looking for Device's locations...")
    for dev in ipfDevs:
        # get device sys_id
        try:
            device_sys_id = ""
            for sNowDevice in sNowDevices:
                if dev["hostname"] == sNowDevice["name"]:
                    device_sys_id = sNowDevice["sys_id"]
                    device_loc = fetchLocationName(sNowDevice, sNowLocations)
                    break
        except:
            print(
                f" No location found for [red]{dev['hostname']}[/red] - sys_id: {device_sys_id}\t\t\t\t\t\t\t\t",
                end="\r",
            )
            device_loc = "NOT IN SNOW"

        devices_loc.append(
            {
                "hostname": dev["hostname"],
                "location": device_loc,
            }
        )
    
    return devices_loc
