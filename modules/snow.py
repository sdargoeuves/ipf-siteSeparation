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


def fetchLocationName(sNowDevice, sNowLocations):
    """
    Take the dictionary for a cmdb_ci_netgear, find the location ID, and extract the location Name from sNowLocations
    """
    location_name = "Location not set in SNOW"
    try:
        device_loc_raw = dict(sNowDevice["location"])
        device_loc_id = device_loc_raw.get("value", "")
        for location in sNowLocations:
            if location["sys_id"] == device_loc_id:
                location_name = location["name"]
                break
    except Exception as exc:
        location_name = "ERR - Fetching location - Not in SNOW"
    return location_name


def fetchSNowDevicesLoc(snow_api: httpx.Client, ipfDevs):
    """
    Function to collect data from SNow and return the JSON containing hostname and site location
    """
    devices_loc = []

    devicesEndpoint = "table/cmdb_ci_netgear"
    locationsEndpoint = "table/cmn_location"
    try:
        sNowDevices_raw = snow_api.get(devicesEndpoint)
        sNowDevices = sNowDevices_raw.json()["result"]
        sNowLocations_raw = snow_api.get(locationsEndpoint)
        sNowLocations = sNowLocations_raw.json()["result"]
        print(f"##INFO## {len(sNowDevices)} devices found in ServiceNow")
    except Exception as exc:
        print(f"##WARNING## Type of error: {type(exc)}")
        print(f"##WARNING## Message: {exc.args}")
        print("##WARNING## Can't process SNow data (server hibernation...)")

    print("##INFO## Looking for Device's location...")
    for dev in ipfDevs:
        try:
            device_sys_id = ""
            for sNowDevice in sNowDevices:
                if dev["hostname"] == sNowDevice["name"]:
                    device_sys_id = sNowDevice["sys_id"]
                    device_loc = fetchLocationName(sNowDevice, sNowLocations)
                    break
            if device_sys_id == "":
                device_loc = "Device not found in SNOW"
        except Exception:
            device_loc = "ERR - Not in SNOW"

        devices_loc.append(
            {
                "hostname": dev["hostname"],
                "location": device_loc,
            }
        )

    return devices_loc