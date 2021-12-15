"""
v1.0
"""

import httpx

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


def fetchSNowDevicesLoc(sNowServer, sNowUser, sNowPass, ipfDevs):
    """
    Function to collect data from SNow and return the JSON containing hostname and site location
    """
    snow_ok = True
    devices_loc = []
    devicesEndpoint = (
        "https://" + sNowServer + "/api/now/v1/cmdb/instance/cmdb_ci_netgear"
    )
    sNowHeaders = {
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        sNowDevices_raw = httpx.get(
            devicesEndpoint, auth=(sNowUser, sNowPass), headers=sNowHeaders, timeout=120
        )
        sNowDevices = sNowDevices_raw.json()["result"]
    except Exception as exc:
        print(f"##WARNING## Type of error: {type(exc)}")
        print(f"##WARNING## Message: {exc.args}")
        print("##WARNING## Can't process SNow data (server hibernation...)")
        snow_ok = False
    for dev in ipfDevs:
        # get device sys_id
        try:
            device_sys = ""
            for sys in sNowDevices:
                if dev["hostname"] == sys["name"]:
                    device_sys = sys["sys_id"]
                    break
            # query the API for that device, and extract the location
            deviceEndpoint = devicesEndpoint + "/" + device_sys
            sNowDevice = httpx.get(
                deviceEndpoint,
                auth=(sNowUser, sNowPass),
                headers=sNowHeaders,
                timeout=120,
            )
            device_loc = sNowDevice.json()["result"]["attributes"]["location"][
                "display_value"
            ]
            print(
                f' Got the device [green]{dev["hostname"]}[/green] in {device_loc} - sys_id: {device_sys}\t\t',
                end="\r",
            )
        except:
            device_loc = "NOT IN SNOW"

        devices_loc.append(
            {
                "hostname": dev["hostname"],
                "location": device_loc,
            }
        )
    if snow_ok:
        print(f"##INFO## info on IPF devices collected from SNow")
    else:
        print(f"##WARNING## Issue with the collection from SNow")
    return devices_loc
