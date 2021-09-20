# import
import sys
import json
import argparse
from typing import List
import pandas as pd
from datetime import datetime
from pandas.core.frame import DataFrame
from rich import print  # Optional

# Module to interact with IP Fabric’s API
from api.ipf_api_client import IPFClient
from modules.readInput import readInput
from modules.sites import getSiteId, getDevicesSnSiteId, updateManualSiteSeparation
from modules.regexRules import (
    regexOptimisation,
    updateSnapshotSettings,
)  # to update regex site separation instead of manual

# Global variables
sNowServer = ""
sNowUser = ""
sNowPass = ""
sNowHeaders = {
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

IPFToken = ""
IPFServer = "https://server.ipfabric.local"
working_snapshot = ""  # if not specified, the last snapshot will be used


def fetchSNowDevicesLoc(sNowServer, sNowUser, sNowPass, ipfDevs):
    """
    Function to collect data from SNow and return the JSON containing hostname and site location
    """
    snow_ok = True
    devices_loc = []
    devicesEndpoint = (
        "https://" + sNowServer + "/api/now/v1/cmdb/instance/cmdb_ci_netgear"
    )
    try:
        sNowDevices_raw = httpx.get(
            devicesEndpoint, auth=(sNowUser, sNowPass), headers=sNowHeaders
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
                deviceEndpoint, auth=(sNowUser, sNowPass), headers=sNowHeaders
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


def updateSnapshotSettings(
    ipf: IPFClient, locations_settings, snapshot_id="", exact_match=False
):
    """
    based on the locations_settings collected from SNow, or read via the input file
    we will create the site separation rules to apply to the snapshot
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


def readInput(source_file):
    """
    Function to read the input file (CSV, XLS, XLSX or JSON) and use this as the source to push data to IP Fabric
    """

    def df_to_json(df_input: DataFrame):
        """
        Sub function to clean the DataFrame from any special character, whitespace, and convert it to a json
        """
        try:
            if not df_input.empty:
                new_headers = ["hostname", "location"]
                for i in range(0, len(df_input.columns) - 2):
                    new_headers.append(i)
                df_input.columns = new_headers
                # we need to remove special character as they cause issues with pushing the data
                # although this could cause hostname to not match the regex on IP Fabric
                special_char = "[\(,\)]"
                df_input["hostname"] = (
                    df_input["hostname"]
                    .str.replace(special_char, "-", regex=True)
                    .str.strip()
                )
                df_input["location"] = (
                    df_input["location"]
                    .str.replace(special_char, "-", regex=True)
                    .str.strip()
                )
                # df_input['hostname'] = df_input['hostname'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
                # df_input['location'] = df_input['location'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
                df_input = df_input.replace("", None).dropna()
                result = df_input.to_json(orient="records")
                return json.loads(result)
            else:
                print(
                    f"##INFO## DataFrame is empty - '{source_file.name}' is not a valid file"
                )
        except Exception as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            print(f"##ERROR## Message: {exc.args}")
            sys.exit(
                f"##ERROR## EXIT -> DataFrame not created - '{source_file.name}' is not a valid file"
            )

    # we initiate an empty DataFramce
    file_df = pd.DataFrame()
    # for a JSON file
    if source_file.name[-4:].lower() == "json":
        try:
            data = json.load(source_file)
        except Exception as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            print(f"##ERROR## Message: {exc.args}")
            sys.exit(
                f"##ERROR## EXIT -> Invalid Data - '{source_file.name}' does not contain JSON data"
            )
    # for a CSV file
    elif source_file.name[-4:].lower() == ".csv":
        file_df = pd.DataFrame(
            pd.read_csv(
                source_file.name,
                sep=None,
                engine="python",
                header=0,
                index_col=False,
                skipinitialspace=True,
            )
        )
        data = df_to_json(file_df)
    # for EXCEL file
    elif (
        source_file.name[-4:].lower() == ".xls"
        or source_file.name[-5:].lower() == ".xlsx"
    ):
        file_df = pd.DataFrame(
            pd.read_excel(source_file.name, header=0, index_col=False)
        )
        data = df_to_json(file_df)
    # otherwise it's not supported
    else:
        print(f"##WARNING## Invalid file - '{source_file.name}' is not a valid file")

    return data


def regexOptimisation(locations_settings, grex=False):
    """
    This function will optimise the rules creation.
    The input is a JSON containing one line per hostname, with the information regarding the site location
    The idea will be to create a set of XX hostnames per regex rule (starting with 10, maybe 20)
    For that we will sort the locations_settings
    """

    def generateHostnames(list_hostnames):
        """
        mini sub function to create the regex using grex if required
        we return the list of devices
        """
        command = ["grex"]
        for h in list_hostnames.split("|"):
            command.append(h)
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except FileNotFoundError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            print(f"##ERROR## Message: {exc.args}")
            sys.exit(
                "##ERROR## EXIT -> GREX is not available - remove the 'grex' option, or install grex: https://github.com/pemistahl/grex#how-to-install"
            )
        print(
            f"##INFO## GREX for hosts: {command[1:2]} to {command[-1:]} \t\t\t\t",
            end="\r",
        )
        return result.stdout

    optimised_regex_list = []
    site_dict = {}
    if grex == True:
        print(f"##INFO## Rules created will using regex generated using 'grex'")
        max_device_per_rule = 20
    else:
        print(f"##INFO## Rules created will use the hostname")
        max_device_per_rule = 10
    # load the json into a DataFrame
    try:
        df = pd.json_normalize(locations_settings)
    except Exception as exc:
        print(f"##ERROR## Type of error: {type(exc)}")
        print(f"##ERROR## Message: {exc.args}")
        sys.exit(
            f"##ERROR## EXIT -> Optimization Failure - could not load the JSON into a DataFrame"
        )

    # Sort by location first, then by hostname
    df_sorted = df.sort_values(by=["location", "hostname"], ignore_index=True)
    counter_device_per_rule = 0
    list_hostnames = ""
    prev_location = ""

    for row in df_sorted.index:
        hostname = df_sorted.at[row, "hostname"]
        location = df_sorted.at[row, "location"]
        # if it's empty, we go to the next iteration
        if prev_location == "":
            list_hostnames = hostname
            prev_location = location
            # print(f"first iteration")
            continue
        # if the location of this device is the same as prev_location, and we haven't reached the limit,
        # we add this to the same rule
        elif prev_location == location:
            if counter_device_per_rule < max_device_per_rule - 1:
                list_hostnames += "|" + hostname
                counter_device_per_rule += 1
            else:
                if grex:
                    site_dict["hostname"] = generateHostnames(list_hostnames)
                else:
                    site_dict["hostname"] = list_hostnames
                site_dict["location"] = prev_location
                optimised_regex_list.append(site_dict)
                # we reset the counter and the prev location
                counter_device_per_rule = 0
                prev_location = location
                list_hostnames = hostname
                site_dict = {}

        # if it's not the same location, we need to save the current regex we have into the dict
        elif prev_location != location:
            if grex:
                site_dict["hostname"] = generateHostnames(list_hostnames)
            else:
                site_dict["hostname"] = list_hostnames
            site_dict["location"] = prev_location
            optimised_regex_list.append(site_dict)
            # we reset the counter and the prev location
            counter_device_per_rule = 0
            prev_location = location
            list_hostnames = hostname
            site_dict = {}

        # if it's the last entry, we need to save
        if row == len(df_sorted) - 1:
            if grex:
                site_dict["hostname"] = generateHostnames(list_hostnames)
            else:
                site_dict["hostname"] = list_hostnames
            site_dict["location"] = location
            optimised_regex_list.append(site_dict)
    return optimised_regex_list


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
        ipf = IPFClient(base_url=IPFServer, token=IPFToken)
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
            ipf = IPFClient(base_url=IPFServer, token=IPFToken)
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
