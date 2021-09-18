# import
import sys
import json
import argparse
import pandas as pd
from datetime import datetime
from pandas.core.frame import DataFrame
from rich import print  # Optional

# Module to interact with IP Fabric’s API
from api.ipf_api_client import IPFClient
from modules.fetchSnow import fetchSNowDevicesLoc
from modules.regexOptimizer import regexOptimisation
from modules.input import readInput

# Global variables
sNowServer = ""
sNowUser = ""
sNowPass = ""


#IPFToken = ""
#IPFServer = "https://server.ipfabric.local"
#working_snapshot = ""  # if not specified, the last snapshot will be used
#IPFToken = ""
#IPFServer = "https://server.ipfabric.local"
#working_snapshot = ""  # if not specified, the last snapshot will be used
#IPFServer = "https://demo7.ipfabric.io/"
#IPFToken = "9c3cfd2352e63385ca9cb36e8678e5fa"
#working_snapshot = "1b80fafc-7674-4299-87b3-1faf7e1b931f"
IPFServer = "https://192.168.220.133/"
IPFToken = "1fb1e37b9d39481af3cf57a6817530be"
working_snapshot = "$last" #this needs to be either $last, $prev, $lastLocked, or the ID of the desired snapshot


def updateManualSiteSeparation(
    ipf: IPFClient, list_devices_sites, snapshot_id="", exact_match=False
):
    """
    based on the locations_settings collected from SNow, or read via the input file
    we will create the manual site separation to apply to the snapshot
    """

    if snapshot_id == "":
        # Fetch last loaded snapshot info from IP Fabric
        snapshot_id = ipf.snapshot_id
    
    url_manual_sep = IPFServer + "v1/sites/manual-separation"
    payload = [{"id": "SITEID","sn": "SN"},{"id": "SITEID","sn": "SN"}]

def SiteId(ipf: IPFClient, locations_settings):
    """
    This function takes each unique locations, and assign it to its id in IP Fabric
    either by finding the existing one, or creating a new siteName
    """
    def findSiteId(site_name):
        """
        return the id of the site matching the name of a site in IPF
        """
        foundSite = False
        # for each site we will look if it exists in IP Fabric, if not we will create it
        for ipf_site in dict_ipf_sites:
            if site_name == ipf_site['siteName']:
                print(f'site in IPF: {site_name}')
                foundSite = True
                return ipf_site['id']
        if not foundSite:
            return createSite(site_name)

    def createSite(site_name):
        """
        create the site with the name provided and return the id of this site.
        """
        #Create the site
        create_new_site_url = IPFServer + "api/v1/sites"
        new_site_payload = {"name": site_name}
        request_new_site = ipf.put(create_new_site_url, json = new_site_payload)
        request_new_site.raise_for_status()
        return request_new_site.json()['id']

    # load the json containing Devices & new Location into a DataFrame
    try:
        df_locations_settings = pd.json_normalize(locations_settings).rename({"hostname": "hostname", "location": "siteName"}, axis=1)
    except Exception as exc:
        print(f"##ERROR## Type of error: {type(exc)}")
        print(f"##ERROR## Message: {exc.args}")
        sys.exit(
            f"##ERROR## EXIT -> Optimization Failure - could not load the JSON into a DataFrame"
        )
    
    # Sort by location first, then by hostname - is it useful?
    #df_sorted = df_locations_settings.sort_values(by=["siteName", "hostname"], ignore_index=True)
    list_new_sites = df_locations_settings["siteName"].unique()

    #Get the Full list of Site in IP Fabric
    request_ipf_sites = ipf.get(IPFServer+"api/v1/sites")
    request_ipf_sites.raise_for_status()
    dict_ipf_sites = request_ipf_sites.json()

    # Creation of the list of dictionnaries containing New and existing sites ID
    list_sites_id = []
    for site_name in list_new_sites:
        dict_new_site = {}
        dict_new_site['siteName'] = site_name
        dict_new_site['id'] = findSiteId(site_name)
        list_sites_id.append(dict_new_site)
    #list_sites_id dict contains: 
    # 'siteName' and 'id' for all sites in IP Fabric, including the ones recently created

    #Let's now merge both tables so we have the hostname sitename and site ID
    df_list_sites_id=pd.json_normalize(list_sites_id)
    list_devices_sites = pd.merge(df_locations_settings, df_list_sites_id, on = "siteName", how = "outer")

    # As we need the SN to push the data into the manual site separation, we're going to repeat the merge
    # with the devDeets this time
    """
    df3 is devDeets.json_normalize
    merge = pd.merge(df3, list_devices_sites, on = "hostname", how = "left")
    merge now contains all devices, plus the new site
    we just need to remove and NaN and replace by catch all
    """


def updateSnapshotSettings(
    ipf: IPFClient, locations_settings, snapshot_id="", exact_match=False
):
    """
    based on the locations_settings collected from SNow, or read via the input file
    we will create the manual site separation to apply to the snapshot
    """

    if snapshot_id == "":
        # Fetch last loaded snapshot info from IP Fabric
        snapshot_id = ipf.snapshot_id
    snapSettingsEndpoint = "/snapshots/" + snapshot_id + "/settings"
    new_settings = {
        "siteSeparation": [],
    }
    if exact_match:
        for loc_setting in locations_settings:
            new_settings["siteSeparation"].append(
                {
                    "note": loc_setting["hostname"],
                    "regex": loc_setting["hostname"],
                    "siteName": loc_setting["location"],
                    "transformation": "none",  # none / uppercase / lowercase
                    "type": "regex",
                }
            )
    else:
        for loc_setting in locations_settings:
            try:
                new_settings["siteSeparation"].append(
                    {
                        "note": loc_setting["hostname"].upper(),
                        "regex": loc_setting["hostname"].upper(),
                        "siteName": loc_setting["location"],
                        "transformation": "uppercase",  # none / uppercase / lowercase
                        "type": "regex",
                    }
                )
            except AttributeError as exc:
                print(f"##ERROR## Type of error: {type(exc)}")
                print(f"##ERROR## Message: {exc.args}")
                sys.exit(
                    "##ERROR## EXIT -> An empty value in the file may have caused this issue. No update done on IP Fabric"
                )
    # last entry will be a "Catch all rule"
    new_settings["siteSeparation"].append(
        {
            "note": "Catch ALL",
            "regex": ".*",
            "siteName": "_catch_all_",
            "transformation": "uppercase",  # none / uppercase / lowercase
            "type": "regex",
        }
    )
    # We update the site separation rules on IP Fabric
    pushSettings = ipf.patch(url=snapSettingsEndpoint, json=new_settings, timeout=60)
    if pushSettings.is_error:
        print(
            f"  --> API PATCH Error - Unable to PATCH data for endpoint: {pushSettings.request}\n      No update done on IP Fabric"
        )
        print("  MESSAGE: ", pushSettings.reason_phrase)
        print("  TIP: An empty value in the CSV could cause this issue")
    else:
        print(f"  --> SUCCESSFULLY Patched settings for snapshot '{snapshot_id}'")


def main(
    source_file=None,
    servicenow=False,
    generate_only=False,
    exact_match=False,
    grex=False,
):
    """
    Main function
    """
    # At least -f or -sn should have been used:
    if source_file == None and not servicenow:
        sys.exit(
            f"##ERROR## You need to specify EITHER the source file, or ServiceNow as the input"
        )
    locations_settings = {}
    # if a source_file was entered as an input, we will read the file
    if source_file != None:
        print(f"##INFO## You've specified the source file: {source_file.name}")
        try:
            locations_settings = readInput(source_file)
        except Exception as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            print(f"##ERROR## Message: {exc.args}")
            sys.exit(
                f"##ERROR## Error while reading the file. Couldn't load the data into a dictionnary"
            )
        if generate_only:
            sys.exit(
                "##INFO## Generate ONLY - you've specified the source file. Nothing to do in this case. Bye Bye!"
            )

    # otherwise we will collect the data from SNow and create the file
    if servicenow:
        print(f"##INFO## Connecting to IP Fabric to collect the list of devices")
        ipf = IPFClient(base_url=IPFServer, token=IPFToken, snapshot_id=working_snapshot)
        devDeets = ipf.device_list(snapshot_id=working_snapshot)
        print(
            f"##INFO## now let's go to SNow to generate the JSON file with hostname/location"
        )
        locations_settings = fetchSNowDevicesLoc(
            sNowServer, sNowUser, sNowPass, devDeets
        )
        # Ouput file name will either be the one given as a source, or auto generated.
        output_file = "".join(
            ["snow_location-", datetime.now().strftime("%Y%m%d-%H%M"), ".json"]
        )
        # Save the locations_settings into the file
        with open(output_file, "w") as json_file:
            json.dump(locations_settings, json_file, indent=2)
        print(
            f"##INFO## file '{json_file.name}' has been created with the info from SNow"
        )
        if generate_only:
            sys.exit("##INFO## Generate ONLY - file has been generated. Bye Bye!")

    # now we are going to get ready to update IP Fabric
    if locations_settings != {}:
        # We create the ipf client if it hasn't been created before
        try:
            ipf, devDeets
        except NameError:
            ipf = IPFClient(base_url=IPFServer, token=IPFToken, snapshot_id=working_snapshot)
            devDeets = ipf.device_list(snapshot_id=working_snapshot)

        # Before pushing the data to IP Fabric we want to optimise the rules
        optimised_locations_settings = regexOptimisation(locations_settings, grex)
        if exact_match:
            print(f"##INFO## Exact match Regex rules will be created\t\t")
        else:
            print(f"##INFO## Uppercase Regex rules will be created\t\t")

        # We can now push this into IP Fabric
        updateSnapshotSettings(
            ipf, optimised_locations_settings, working_snapshot, exact_match
        )
        # updateSnapshotSettings(ipf, locations_settings, "0ab031b1-19ba-44dd-b708-4185bd01c819", exact_match)
    print("##INFO## End of the script. Bye Bye!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Specify the source file containing the host/location details OR you can select to use ServiceNow as the source\n"
    )
    group_source = parser.add_mutually_exclusive_group()
    group_source.add_argument(
        "-f",
        "--file",
        metavar="source_file",
        type=argparse.FileType("rt"),
        help="Source file, as a JSON/CSV/XLS/XLSX file containing hostname/site information",
    )
    group_source.add_argument(
        "-snow",
        "--servicenow",
        dest="servicenow",
        action="store_true",
        default=False,
        help="Script will collect for each device in IP Fabric the location in ServiceNow and store this as JSON",
    )
    parser.add_argument(
        "-g",
        "--generate",
        dest="generate",
        action="store_true",
        default=False,
        help="use to only generate a new host/site JSON file from SNow. This won't update IP Fabric",
    )
    parser.add_argument(
        "-e",
        "--exact_match",
        dest="exact_match",
        action="store_true",
        default=False,
        help="by default the regex and hostname will be capitalised in the regex. Use this option to keep the case from CSV/SNow",
    )
    parser.add_argument(
        "-grex",
        "--grex",
        dest="grex",
        action="store_true",
        default=False,
        help="instead of using list of hostname, we use GREX to find the regex matching that same list",
    )
    args = parser.parse_args()

    main(args.file, args.servicenow, args.generate, args.exact_match, args.grex)
