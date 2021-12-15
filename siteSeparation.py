"""
Version 1.2 - 2021/12/14
NOW USING: pip install ipfabric

- Site Separation script -
This script will allow you to use an external source to change the Site Separation of IP Fabric.

External source can either be:
 - a file (csv, xls, xlsx, json)
 - ServiceNow API

The recommended option will use Manual Site Separation. There is also an option to use rules creation.
To execute the script:
> python3 siteSeparation.py -f source_file
or
> python3 siteSeparation.py -snow
or to create Site Separation Rules:
> python3 siteSeparation.py -f source_file -u

"""
# import
import sys
import json
import argparse
from datetime import datetime
from rich import print  # Optional

# Module to interact with IP Fabric’s API
from ipfabric import IPFClient
from modules.readInput import readInput
from modules.sites import getSiteId, getDevicesSnSiteId, updateManualSiteSeparation
from modules.regexRules import (
    regexOptimisation,
    updateSnapshotSettings,
)

# Or ServiceNow
from modules.snow import fetchSNowDevicesLoc

# ServiceNow variables
sNowServer = "dev103869.service-now.com/"
sNowUser = "ipfabric"
sNowPass = "IPFabric01!"

# IP Fabric variables
IPFServer = "https://ipfabric.server"
IPFToken = "token"
working_snapshot = ""
# string to use for the catch all sites, all /devices in IP Fabric which are not linked to any sites from the source
catch_all = "_catch_all_"
# define the number of hostname per line in the Site Separation Rules
max_devices_per_rule = 20


def main(
    source_file=None,
    servicenow=False,
    generate_only=False,
    upper_match=False,
    exact_match=False,
    grex=False,
    reg_out=False,
    keep_rules=False,
):
    """
    Main function
    """

    # List of required columns for the device inventory
    inventory_devices_columns = [
        "hostname",
        "siteName",
        "loginIp",
        "loginType",
        "vendor",
        "platform",
        "family",
        "version",
        "sn",
        "devType",
    ]

    # At least -f or -sn should have been used:
    if source_file is None and not servicenow:
        sys.exit(
            f"##ERROR## You need to specify EITHER the source file, or ServiceNow as the input"
        )
    locations_settings = {}
    # if a source_file was entered as an input, we will read the file
    if source_file is not None:
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
        ipf = IPFClient(
            base_url=IPFServer, token=IPFToken, snapshot_id=working_snapshot
        )
        devDeets = ipf.inventory.devices.all(columns=inventory_devices_columns)
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
            ipf = IPFClient(
                base_url=IPFServer, token=IPFToken, snapshot_id=working_snapshot
            )
            devDeets = ipf.inventory.devices.all(columns=inventory_devices_columns)
        # Site Separation using RULES - not the recommended way
        if upper_match or exact_match or grex:
            # Before pushing the data to IP Fabric we want to optimise the rules
            optimised_locations_settings = regexOptimisation(
                locations_settings, grex, max_devices_per_rule
            )
            if exact_match:
                print(f"##INFO## Exact match Regex rules will be created\t\t")
            else:
                print(f"##INFO## Uppercase Regex rules will be created\t\t")

            # We can now push this into IP Fabric
            updateSnapshotSettings(
                ipf,
                optimised_locations_settings,
                exact_match,
                reg_out,
                keep_rules,
            )
        # Site Separation using Manual Site Separation - the recommended way
        else:
            # We now need to check the list of new sites, match them and create them in IP Fabric if they don't exist
            list_devices_sitesID = getSiteId(ipf, locations_settings, catch_all)

            # We create the list to push via Manual Site separation. It needs the SN of the devices, and the ID of the site
            list_devices_sites_to_push = getDevicesSnSiteId(
                devDeets, list_devices_sitesID
            )

            # Finally we update the settings of the manual site separation
            updateManualSiteSeparation(ipf, list_devices_sites_to_push)
            # updateSnapshotSettings(ipf, locations_settings, "0ab031b1-19ba-44dd-b708-4185bd01c819", exact_match)
    print("##INFO## End of the script. Bye Bye!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=" - Site Separation script -\n\
Specify the source file containing the host/location details OR you can select to use ServiceNow as the source.\n\
Recommended option will use Manual Site Separation. There is also an option to use rules creation, which is not recommended.\n\n\
> python3 siteSeparation.py -f source_file",
        formatter_class=argparse.RawTextHelpFormatter,
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
    group_rules = parser.add_argument_group(
        "Group for Rules creation",
        "This is not the recommended method to update Site Separation, use with caution",
    )
    group_match_case = group_rules.add_mutually_exclusive_group()
    group_match_case.add_argument(
        "-u",
        "--upper_match",
        dest="upper_match",
        action="store_true",
        default=False,
        help="(Rules creation) the hostname will be capitalised in the regex rules",
    )
    group_match_case.add_argument(
        "-e",
        "--exact_match",
        dest="exact_match",
        action="store_true",
        default=False,
        help="(Rules creation) use this option to keep the case from the source (file or Snow)",
    )
    group_match_case.add_argument(
        "-grex",
        "--grex",
        dest="grex",
        action="store_true",
        default=False,
        help="(Rules creation) instead of using list of hostname, we use GREX to find the regex matching that same list",
    )
    group_rules.add_argument(
        "-reg_out",
        "--regex_output",
        dest="reg_out",
        action="store_true",
        default=False,
        help="(Rules creation) use this option to generate the JSON containing the rules to be pushed. By using this option, you will not update the IP Fabric settings",
    )
    group_rules.add_argument(
        "-k",
        "--keep",
        dest="keep_rules",
        action="store_true",
        default=False,
        help="(Rules creation) use this option if you want to KEEP existing rules: add new rules on top of the existing ones from the latest or working_snapshot **NOT RECOMMENDED**",
    )

    args = parser.parse_args()

    main(
        args.file,
        args.servicenow,
        args.generate,
        args.upper_match,
        args.exact_match,
        args.grex,
        args.reg_out,
        args.keep_rules,
    )
