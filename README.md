# siteSeparation.py
A script to use either ServiceNow or an input file (csv/xls/xlsx/json) to generate the site separation for IP Fabric

## API folder
contains the IP Fabric API client - [GitHub page] [api_client_ipf]


## How to use

***to use ServiceNow:***
```sh
python3 siteSeparation.py -sn
```
***to use a source file***
```sh
python3 siteSeparation.py -f a_file.xlsx
```

## Requirements.txt

Find the required library in order for this script to work

| Library | Description |
| ------ | ------ |
| httpx | Mandatory - HTTP client |
| pandas | Mandatory - Data Analysis |
| *openpyxl* | *Optional - only needed to support XLSX file* |
| *xlrd* | *Optional - only needed to support XLS file* |
| *rich* | *Optional - Enhance terminal formatting* |

## GREX

To use *regex* instead of hostname inside the rules which will be generated, this script is using the tool [GREX][grex_github]
For this option to work, you need to have grex installed. You can follow the instruction [here][grex_install]

## Help

  - -f source_file, --file source_file
Source file, as a JSON/CSV/XLS/XLSX file containing hostname/site information
  - -snow, --servicenow
  Script will collect for each device in IP Fabric the location in ServiceNow and store this as JSON
  - -g, --generate
  use to only generate a new host/site JSON file from SNow. This won't update IP Fabric
  - -e, --exact_match
  by default the regex and hostname will be capitalised in the regex. Use this option to keep the case from CSV/SNow
  -grex, --grex
  instead of using list of hostname, we use GREX to find the regex matching that same list


## License

MIT

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [api_client_ipf]: <https://github.com/community-fabric/integration-demos/tree/main/api_clients/ipf>
   [grex_github]: <https://github.com/pemistahl/grex>
   [grex_install]:<https://github.com/pemistahl/grex#how-to-install>