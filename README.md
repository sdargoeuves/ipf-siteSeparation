# siteSeparation.py
This script will allow you to use an external source to change the Site Separation of IP Fabric.
To do so, the script will use **Manual Site Separation**, which is the recommended way to update the settings.
*The option to generate rules based on hostname is also available, but not recommended.*


## API folder
contains the IP Fabric API client - [GitHub page] [api_client_ipf]


## How to use

***to use ServiceNow:***
```sh
python3 siteSeparation.py -snow
```
***to use a source file***
```sh
python3 siteSeparation.py -f source_file.xlsx 
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
*This is not the recommended method to update Site Separation, use with caution*

- *-u, --upper_match*

*(Rules creation) the hostname will be capitalised in the regex rules*
- *-e, --exact_match*

*(Rules creation) use this option to keep the case from the source (file or Snow)*
- *-grex, --grex*

*(Rules creation) instead of using list of hostname, we use GREX to find the regex matching that same list*
- *-reg_out, --regex_output*

*(Rules creation) use this option to generate the JSON containing the rules to be pushed. By using this option, you will not update the IP Fabric settings*


## License

MIT

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [api_client_ipf]: <https://github.com/community-fabric/integration-demos/tree/main/api_clients/ipf>
   [grex_github]: <https://github.com/pemistahl/grex>
   [grex_install]:<https://github.com/pemistahl/grex#how-to-install>