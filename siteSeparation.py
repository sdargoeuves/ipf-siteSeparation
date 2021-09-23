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
from modules.snow import fetchSNowDevicesLoc
from modules.readInput import readInput
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


IPFServer = "https://demo7.ipfabric.io"
IPFToken = "9c3cfd2352e63385ca9cb36e8678e5fa"
#working_snapshot = "1b80fafc-7674-4299-87b3-1faf7e1b931f"

def main(
    source_file=None,
    servicenow=False,
    generate_only=False,
    exact_match=False,
    grex=False,
    reg_out=False,
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
            ipf,
            optimised_locations_settings,
            working_snapshot,
            exact_match,
            reg_out,
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
    parser.add_argument(
        "-reg_out",
        "--regex_output",
        dest="reg_out",
        action="store_true",
        default=False,
        help="Use this option to generate the JSON containing the rules to be pushed. By using this option, you will not update the IP Fabric settings",
    )
    args = parser.parse_args()

    main(
        args.file,
        args.servicenow,
        args.generate,
        args.exact_match,
        args.grex,
        args.reg_out,
    )
