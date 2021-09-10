# siteSeparatio.py
A script to use either ServiceNow or an input file (csv/xls/xlsx/json) to generate the site separation for IP Fabric

## API
contains the IP Fabric API client. this is available here: (https://github.com/community-fabric/integration-demos/tree/main/api_clients/ipf)

## How to use

***to use ServiceNow:***
python3 siteSeparation.py -sn

***to use a file***
python3 siteSeparation.py -f a_file.xlsx

## Help
  -f source_file, --file source_file
                        Source file, as a JSON/CSV/XLS/XLSX file containing hostname/site information
  -snow, --servicenow   Script will collect for each device in IP Fabric the location in ServiceNow and store this as JSON
  -g, --generate        use to only generate a new host/site JSON file from SNow. This won't update IP Fabric
  -e, --exact_match     by default the regex and hostname will be capitalised in the regex. Use this option to keep the case from CSV/SNow
  -grex, --grex         instead of using list of hostname, we use GREX to find the regex matching that same list

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

