# siteSeparation.py
This script will allow you to use an external source to change the Site Separation of IP Fabric.
To do so, the script will use **Manual Site Separation**.
*The option to generate rules based on hostname is also available*

Since IP Fabric v4.3, the manual site separation is using **Device Attributes**.
The script will update the relevant settings depending on your version.
>With IP Fabric >=4.3  only Manual Site Separation / Attribute update is available, rules creation will be added at a later stage.

## How to install

***Install ipfabric Python module and dependencies***
```sh
pip install -r requirements.txt
```

## How to use

***to use ServiceNow:***
```sh
python3 siteSeparation.py -snow
```
***to use a source file to update Manual Site Separation***
```sh
python3 siteSeparation.py -f source_file.xlsx 
```
***to use a source file to create Site Rules***
```sh
python3 siteSeparation.py -f source_file.csv --upper_match
```

## Requirements.txt

Find the required library in order for this script to work

| Library | Description |
| ------ | ------ |
| ipfabric | Mandatory - [IP Fabric python module][ipfabric-python] |
| httpx | Mandatory - HTTP client |
| pandas  | Mandatory - Data Analysis |
| *openpyxl* | *Optional - only needed to support XLSX file* |
| *xlrd* | *Optional - only needed to support XLS file* |
| *rich* | *Optional - Enhance terminal formatting* |

## GREX

There is an option to generate *regex* based on the hostnames, instead of just using hostname in the rules for the site separation.
> `GREX` is required for this option to work
> To install, you can follow these [instructions][grex_install]

[Find more information about GREX][grex_github]


## Help

- -f source_file, --file source_file

Source file, as a JSON/CSV/XLS/XLSX file containing hostname/site information
- -snow, --servicenow

Script will collect for each device in IP Fabric the location in ServiceNow and store this as JSON
- -g, --generate

use to only generate a new host/site JSON file from SNow. This won't update IP Fabric

*Group for Rules creation:*
*This is not the recommended method to update Site Separation*

- *-u, --upper_match*

*(Rules creation) the hostname will be capitalised in the regex rules*
- *-e, --exact_match*

*(Rules creation) use this option to keep the case from the source (file or Snow)*
- *-grex, --grex*

*(Rules creation) instead of using list of hostname, we use GREX to find the regex matching that same list*
- *-reg_out, --regex_output*

*(Rules creation) use this option, with -u or -e or -grex, to generate the JSON containing the rules to be pushed. By using this option, you will not update the IP Fabric settings*
- *-k, --keep*

*(Rules creation) use this option, with -u or -e or -grex, if you want to KEEP existing rules: add new rules on top of the existing ones from the latest or working_snapshot \*\*NOT RECOMMENDED as it could lead to duplicate rules and performance issue\*\**


## License

MIT

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [ipfabric-python]: <https://github.com/community-fabric/python-ipfabric>
   [grex_github]: <https://github.com/pemistahl/grex>
   [grex_install]:<https://github.com/pemistahl/grex#how-to-install>
