import sys
import json
import pandas as pd
from pandas.core.frame import DataFrame


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

