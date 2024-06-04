# Wazuh SCA Solution

## Overview
This project provides a solution for Security Configuration Assessment (SCA) using Wazuh.
The solution includes checks, rules, and remediations to ensure compliance with security benchmarks.

In summary, `sca_check.py` automates the process of analyzing system configurations and applying solutions to 
ensure compliance with security standards, with a focus on leveraging Wazuh's tailored remediation strategies.

## Prerequisites
- Python 3.x installed on your system.
- PyYAML library installed (`pip install PyYAML` if not already installed).
- Sudo Privileges

## Syntax
`python sca_check.py cis_path [solutions_path] [whitelisted_checks]`

### Arguments
- `cis_path` (mandatory): The path or URL to the CIS benchmark file in YAML format.
- `solutions_path` (optional): The path or URL to the Wazuh SCA solutions file in YAML format. 
- `whitelisted_checks` (optional): comma-separated list of check ids (if given only these checks will be checked). 

### Note
If `solutions_path` is not specified, the script will attempt to find it beside the `cis_path` and ending in `_solutions.yml`. <br>
For example if `cis_path` is set to`/path/to/cis_my_os_version.yml` <br>
then the `solutions_path` will be `/path/to/cis_my_os_version_solutions.yml`

## Lazy Tips
Run the script without downloading the repository:
#### Alma Linux 8
`bash -c "$(curl -s "https://raw.githubusercontent.com/Elyasnz/wazuh-sca-solution/master/sca_rules/alma/8/apply")"`
#### Ubuntu 22-04
`bash -c "$(curl -s "https://raw.githubusercontent.com/Elyasnz/wazuh-sca-solution/master/sca_rules/ubuntu/22-04/apply")"`

## Contributing
To contribute, please fork the repository, create a feature branch, and submit a pull request.