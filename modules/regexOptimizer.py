import subprocess

"""

"""

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
