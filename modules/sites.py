import sys
import json
from typing import List
import pandas as pd
from rich import print  # Optional

# Module to interact with IP Fabric’s API
from api.ipf_api_client import IPFClient


def updateManualSiteSeparation(
    ipf: IPFClient, list_devicesSn_sitesId: List, snapshot_id=None
):
    """
    based on the locations_settings collected from SNow, or read via the input file
    we will create the manual site separation to apply to the snapshot
    """
    if snapshot_id == "":
        # Fetch last snapshot info from IP Fabric
        snapshot_id = ipf.fetch_last_snapshot_id()

    # we load the list into a JSON
    json_devicesSn_sitesId = json.loads(list_devicesSn_sitesId)

    # Creation of the request to push the manual site separation
    url_manual_sep = "sites/manual-separation"
    payload = {
        "sites": json_devicesSn_sitesId,
        "snapshot": snapshot_id or ipf.snapshot_id,
    }
    print(
        f"##INFO## Manual Site Separation will be pushed for {len(json_devicesSn_sitesId)} devices"
    )
    push_newsites = ipf.post(url=url_manual_sep, json=payload, timeout=120)
    push_newsites.raise_for_status()
    # This endpoint doesn't return 200 when successful
    if push_newsites.status_code == 204:
        # Now we change the sitespearation settings to manual
        url_site_sep_settings = "settings"
        site_sep_settings = {"siteTypeCalc": "manual"}
        print(f"##INFO## Changing settings to use Manual Site Separation...")
        push_site_settings = ipf.patch(
            url=url_site_sep_settings, json=site_sep_settings, timeout=120
        )
        push_site_settings.raise_for_status()
        if not push_site_settings.is_error:
            print(f"##INFO## Manual site separation has been udpated!")
        else:
            print(
                f"##WARNING## Settings for site separation have not been updated... return code: {push_site_settings.status_code}"
            )
    else:
        print(
            f"##WARNING## Manual site separation has not been updated... return code: {push_newsites.status_code}"
        )


def getSiteId(ipf: IPFClient, locations_settings, catch_all):
    """
    This function takes each unique locations, and assign it to its id in IP Fabric
    either by finding the existing one, or creating a new siteName
    """

    def findSiteId(ipf, site_name):
        """
        return the id of the site matching the name of a site in IPF
        """
        foundSite = False
        # for each site we will look if it exists in IP Fabric, if not we will create it
        for ipf_site in dict_ipf_sites:
            if site_name == ipf_site["siteName"]:
                foundSite = True
                return ipf_site["id"]
        if not foundSite:
            print(f"##INFO## new site created in IPF: {site_name}")
            return createSite(ipf, site_name)

    def createSite(ipf, site_name):
        """
        create the site with the name provided and return the id of this site.
        """
        # Create the site
        create_new_site_url = "sites"
        new_site_payload = {"name": site_name}
        request_new_site = ipf.put(url=create_new_site_url, json=new_site_payload)
        request_new_site.raise_for_status()
        return request_new_site.json()["id"]

    # load the json containing Devices & new Location into a DataFrame
    try:
        df_locations_settings = pd.json_normalize(locations_settings).rename(
            {"hostname": "hostname", "location": "siteName"}, axis=1
        )
    except Exception as exc:
        print(f"##ERROR## Type of error: {type(exc)}")
        print(f"##ERROR## Message: {exc.args}")
        sys.exit(
            f"##ERROR## EXIT -> Optimization Failure - could not load the JSON into a DataFrame"
        )

    # Sort by location first, then by hostname - is it useful?
    # df_sorted = df_locations_settings.sort_values(by=["siteName", "hostname"], ignore_index=True)
    list_new_sites = df_locations_settings["siteName"].unique()

    # Get the Full list of Site in SiteSeparation in IP Fabric
    request_ipf_sites = ipf.get(url="sites")
    request_ipf_sites.raise_for_status()
    dict_ipf_sites = request_ipf_sites.json()

    # Creation of the list of dictionnaries containing New and existing sites ID
    list_sites_id = []
    for site_name in list_new_sites:
        dict_new_site = {}
        dict_new_site["siteName"] = site_name
        dict_new_site["id"] = findSiteId(ipf, site_name)
        list_sites_id.append(dict_new_site)
    # list_sites_id dict contains:
    # 'siteName' and 'id' for all sites in IP Fabric, including the ones recently created

    ## we need to add the "_catch_all_" site
    list_sites_id.append({"siteName": catch_all, "id": findSiteId(ipf, catch_all)})

    # Let's now merge both tables so we have the hostname sitename and site ID
    df_list_sites_id = pd.json_normalize(list_sites_id)
    list_devices_sites = pd.merge(
        df_locations_settings, df_list_sites_id, on="siteName", how="outer"
    )

    return list_devices_sites


def getDevicesSnSiteId(ipf_devices, list_devices_sitesID):

    # As we need the SN to push the data into the manual site separation, we're going to repeat the merge
    # with the devDeets this time

    """
    df3 is devDeets.json_normalize
    merge = pd.merge(df3, list_devices_sites, on = "hostname", how = "left")
    merge now contains all devices, plus the new site
    we just need to remove and NaN and replace by catch all

    df_ipf_devices = pd.json_normalize(devDeets)
    merge_list = pd.merge(df_ipf_devices, list_devices_sites, on = "hostname", how = "left").fillna("_catch_all_", inplace=True)

    list_devices_sites.siteName.values[-1] == "_catch_all_"
    list_devices_sites.id.values[-1] == "id of the _catch_all_"
    merge_list.siteName_y.fillna(list_devices_sites.siteName.values[-1], inplace=True)
    merge_list.id.fillna(list_devices_sites.id.values[-1], inplace=True)
    merge_list.drop(columns=['column_nameA', 'column_nameB'], inplace=True)

    """

    df_ipf_devices = pd.json_normalize(ipf_devices)
    # cleaning up this DF by removing unwanted columns
    df_ipf_devices.drop(
        columns=[
            "siteName",
            "loginIp",
            "loginType",
            "vendor",
            "platform",
            "family",
            "version",
            "devType",
        ],
        inplace=True,
    )
    
    ## UPPER both DF hostname to ensure it's not case sensitive
    df_ipf_devices["hostname"] = df_ipf_devices["hostname"].str.upper()
    list_devices_sitesID["hostname"] = list_devices_sitesID["hostname"].str.upper()
    
    # We now merge the list of devices from IP Fabric, with the list of Sites and their ID
    merge_list = pd.merge(
        df_ipf_devices, list_devices_sitesID, on="hostname", how="left"
    )
    # the _catch_all_ sites need to be filled for any sites not from the source file
    # the last entry from that list is the catch all site
    merge_list.siteName.fillna(list_devices_sitesID.siteName.values[-1], inplace=True)
    merge_list.id.fillna(list_devices_sitesID.id.values[-1], inplace=True)
    merge_list.drop(columns=["hostname", "siteName"], inplace=True)
    return merge_list.to_json(orient="records")
