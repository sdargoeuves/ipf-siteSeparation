"""
Version 1.1 - 2021/12/02
"""

import sys
import subprocess
from datetime import datetime
import json
import pandas as pd
#from api.ipf_api_client import IPFClient
from ipfabric import IPFClient


def regexOptimisation(locations_settings, grex=False, max_devices_per_rule=20):
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
            print(f"##ERR## Type of error: {type(exc)}")
            print(f"##ERR## Message: {exc.args}")
            sys.exit(
                "##ERR## EXIT -> GREX is not available - remove the 'grex' option, or install grex: https://github.com/pemistahl/grex#how-to-install"
            )
        print(
            f"##INFO## GREX for hosts: {command[1:2]} to {command[-1:]} \t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t",
            end="\r",
        )
        return result.stdout[:-1]

    optimised_regex_list = []
    site_dict = {}
    if grex == True:
        print(f"##INFO## Rules created will using regex generated using 'grex'")
    else:
        print(f"##INFO## Rules created will use the hostname")
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
    try:
        df_sorted = df.sort_values(by=["location", "hostname"], ignore_index=True)
    except KeyError as exc:
        print(f"##ERROR## Type of error: {type(exc)}")
        print(f"##ERROR## Message: {exc.args}")
        sys.exit(
            f"##ERROR## EXIT -> Optimization Failure - could not sort the DataFrame based on location/hostname. Check the source file."
        )
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
            if counter_device_per_rule < max_devices_per_rule - 1:
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


def updateSnapshotSettings(
    ipf: IPFClient,
    locations_settings,
    exact_match=False,
    reg_out=False,
    keep_rules=False,
):
    """
    based on the locations_settings collected from SNow, or read via the input file
    we will create the site separation rules to apply to the snapshot
    """
    snapSettingsEndpoint = "/snapshots/" + ipf.snapshot_id + "/settings"
    new_settings = {
        "siteTypeCalc": "rules",
        "siteSeparation": [],
    }
    create_catch_all_rule = True
    # Creation of the list containing the new rules to push, one with exact match to keep the case sensitivity and the other one UPPER match.
    if exact_match:
        for loc_setting in locations_settings:
            new_settings["siteSeparation"].append(
                {
                    "note": " >> ".join([loc_setting["hostname"], loc_setting["location"]]),
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
                        "note": " >> ".join([loc_setting["hostname"], loc_setting["location"]]),
                        "regex": loc_setting["hostname"].upper(),
                        "siteName": loc_setting["location"],
                        "transformation": "uppercase",  # none / uppercase / lowercase
                        "type": "regex",
                    }
                )
            except AttributeError as exc:
                print(f"##ERR## Type of error: {type(exc)}")
                print(f"##ERR## Message: {exc.args}")
                sys.exit(
                    "##ERR## EXIT -> An empty value in the file may have caused this issue. No update done on IP Fabric"
                )

    # if you want the JSON output, we will create the file, and not update IP Fabric
    if reg_out:
        print("")
        # Ouput file name will either be the one given as a source, or auto generated.
        output_file = "".join(
            ["regex_rules-", datetime.now().strftime("%Y%m%d-%H%M"), ".json"]
        )
        # Save the locations_settings into the file
        with open(output_file, "w") as json_file:
            json.dump(new_settings["siteSeparation"], json_file, indent=2)
        print(
            f"##INFO## file '{json_file.name}' has been created with the Rules information. No update done on IP Fabric"
        )
        return
    
    # only if we are deleting the existing rules
    if keep_rules:
        print(f"\n##WARNING## You are ADDING rules on top of existing ones. This may creates duplicate rules and affect performance.\n")
        #previous_rules = ipf.get("/settings/site-separation").json()["data"]
        #We collect existing rules for the snapshot used to create the class IPF
        previous_rules = ipf.get("/snapshots/" + ipf.snapshot_id + "/settings").json()["siteSeparation"]
        #if there are previous rules, we won't need to add the the catch all at the end
        if previous_rules != []:
            create_catch_all_rule = False
            rule_id = 0
            for rule in new_settings["siteSeparation"]:
                previous_rules.insert(rule_id, rule)
                rule_id += 1
            new_settings["siteSeparation"] = previous_rules

    # last entry will be a "Catch all rule", only if we are deleting the existing rules
    if create_catch_all_rule:
        new_settings["siteSeparation"].append(
            {
                "note": "Catch ALL",
                "regex": ".*",
                "siteName": "_catch_all_",
                "transformation": "uppercase",  # none / uppercase / lowercase
                "type": "regex",
            }
        )
    # We update the site separation rules on IP Fabric for that snapshot
    pushSettings = ipf.patch(
        url=snapSettingsEndpoint, json=new_settings, timeout=120
    )
    if pushSettings.is_error:
        print(
            f"  --> API PATCH Error - Unable to PATCH data for endpoint: {pushSettings.request}\n      No update done on IP Fabric"
        )
        print("  MESSAGE: ", pushSettings.reason_phrase)
        print("  TIP: An empty value in the CSV could cause this issue")
    else:
        print(
            f"  --> SUCCESSFULLY Patched settings for snapshot '{ipf.snapshot_id}'"
        )

        # we also update the global settings with the same rules:
        globalSettingsEndpoint = "/settings/site-separation"
        pushGlobalSettings = ipf.put(
            url=globalSettingsEndpoint,
            json=new_settings["siteSeparation"],
            timeout=120,
        )
        if pushGlobalSettings.is_error:
            print(
                f"  --> API PATCH Error - Unable to PATCH data for endpoint: {pushGlobalSettings.request}\n      No update done on IP Fabric"
            )
            print("  MESSAGE: ", pushGlobalSettings.reason_phrase)
            print("  TIP: An empty value in the CSV could cause this issue")
        else:
            print(f"  --> SUCCESSFULLY Patched global settings")

            # Once done, we need to update the Site Separation settings to ensure we will use USer Rules from this point
            url_site_sep_settings = "settings"
            site_sep_settings = {"siteTypeCalc": "rules"}
            print(f"##INFO## Changing settings to use Rules Site Separation...")
            push_site_settings = ipf.patch(
                url=url_site_sep_settings, json=site_sep_settings, timeout=120
            )
            push_site_settings.raise_for_status()
            if not push_site_settings.is_error:
                print(f"##INFO## Site separation has been udpated!")
            else:
                print(
                    f"##WARNING## Settings for site separation have not been updated... return code: {push_site_settings.status_code}"
                )




def updateSnapshotSettings_v4_3(
    ipf: IPFClient,
    locations_settings,
    exact_match=False,
    reg_out=False,
    keep_rules=False,
):
    """
    based on the locations_settings collected from SNow, or read via the input file
    we will create the site separation rules to apply to the snapshot
    """
    snapSettingsEndpoint = "/snapshots/" + ipf.snapshot_id + "/settings"
    new_settings = {
        "siteSeparation": {
            "manualEnabled": False,
            "neighborshipFallbackEnabled": True,
            "rules": [
                {
                    "id": "468eca77-d66b-428d-b1db-6d96d112b45f",
                    "note": "^L33R[79]$ >> L33",
                    "regex": "^L33R[79]$",
                    "siteName": "L33",
                    "transformation": "none",
                    "type": "regexHostname"
                }
            ]
        }
    }
    create_catch_all_rule = True
    # Creation of the list containing the new rules to push, one with exact match to keep the case sensitivity and the other one UPPER match.
    if exact_match:
        for loc_setting in locations_settings:
            new_settings["siteSeparation"]["rules"].append(
                {
                    "note": " >> ".join([loc_setting["hostname"], loc_setting["location"]]),
                    "regex": loc_setting["hostname"],
                    "siteName": loc_setting["location"],
                    "transformation": "none",  # none / uppercase / lowercase
                    "type": "regexHostname",
                }
            )
    else:
        for loc_setting in locations_settings:
            try:
                new_settings["siteSeparation"]["rules"].append(
                    {
                        "note": " >> ".join([loc_setting["hostname"], loc_setting["location"]]),
                        "regex": loc_setting["hostname"].upper(),
                        "siteName": loc_setting["location"],
                        "transformation": "uppercase",  # none / uppercase / lowercase
                        "type": "regexHostname",
                    }
                )
            except AttributeError as exc:
                print(f"##ERR## Type of error: {type(exc)}")
                print(f"##ERR## Message: {exc.args}")
                sys.exit(
                    "##ERR## EXIT -> An empty value in the file may have caused this issue. No update done on IP Fabric"
                )

    # if you want the JSON output, we will create the file, and not update IP Fabric
    if reg_out:
        print("")
        # Ouput file name will either be the one given as a source, or auto generated.
        output_file = "".join(
            ["regex_rules-", datetime.now().strftime("%Y%m%d-%H%M"), ".json"]
        )
        # Save the locations_settings into the file
        with open(output_file, "w") as json_file:
            json.dump(new_settings["siteSeparation"], json_file, indent=2)
        print(
            f"##INFO## file '{json_file.name}' has been created with the Rules information. No update done on IP Fabric"
        )
        return
    
    # only if we are deleting the existing rules
    if keep_rules:
        print(f"\n##WARNING## You are ADDING rules on top of existing ones. This may creates duplicate rules and affect performance.\n")
        #previous_rules = ipf.get("/settings/site-separation").json()["data"]
        #We collect existing rules for the snapshot used to create the class IPF
        previous_rules = ipf.get("/snapshots/" + ipf.snapshot_id + "/settings").json()["siteSeparation"]
        #if there are previous rules, we won't need to add the the catch all at the end
        if previous_rules != []:
            create_catch_all_rule = False
            rule_id = 0
            for rule in new_settings["siteSeparation"]["rules"]:
                previous_rules["rules"].insert(rule_id, rule)
                rule_id += 1
            new_settings["siteSeparation"] = previous_rules

    # last entry will be a "Catch all rule", only if we are deleting the existing rules
    if create_catch_all_rule:
        new_settings["siteSeparation"]["rules"].append(
            {
                "note": "Catch ALL",
                "regex": ".*",
                "siteName": "_catch_all_",
                "transformation": "uppercase",  # none / uppercase / lowercase
                "type": "regexHostname",
            }
        )
    # We update the site separation rules on IP Fabric for that snapshot
    pushSettings = ipf.patch(
        url=snapSettingsEndpoint, json=new_settings, timeout=120
    )
    if pushSettings.is_error:
        print(
            f"  --> API PATCH Error - Unable to PATCH data for endpoint: {pushSettings.request}\n      No update done on IP Fabric"
        )
        print("  MESSAGE: ", pushSettings.reason_phrase)
        print("  TIP: An empty value in the CSV could cause this issue")
    else:
        print(
            f"  --> SUCCESSFULLY Patched settings for snapshot '{ipf.snapshot_id}'"
        )

        # we also update the global settings with the same rules:
        globalSettingsEndpoint = "/settings/site-separation"
        pushGlobalSettings = ipf.put(
            url=globalSettingsEndpoint,
            json=new_settings["siteSeparation"],
            timeout=120,
        )
        if pushGlobalSettings.is_error:
            print(
                f"  --> API PATCH Error - Unable to PATCH data for endpoint: {pushGlobalSettings.request}\n      No update done on IP Fabric"
            )
            print("  MESSAGE: ", pushGlobalSettings.reason_phrase)
            print("  TIP: An empty value in the CSV could cause this issue")
        else:
            print(f"  --> SUCCESSFULLY Patched global settings")

            # Once done, we need to update the Site Separation settings to ensure we will use USer Rules from this point
            url_site_sep_settings = "settings"
            site_sep_settings = {"siteTypeCalc": "rules"}
            print(f"##INFO## Changing settings to use Rules Site Separation...")
            push_site_settings = ipf.patch(
                url=url_site_sep_settings, json=site_sep_settings, timeout=120
            )
            push_site_settings.raise_for_status()
            if not push_site_settings.is_error:
                print(f"##INFO## Site separation has been udpated!")
            else:
                print(
                    f"##WARNING## Settings for site separation have not been updated... return code: {push_site_settings.status_code}"
                )
