# Schools Change Detection

Scripts for checking the MOE Schools data against NZ Facilities data to identify updates needed. Returns a geopackage containing information about updates, deletions and additions needed.

## Before you begin

This script is best executed using Conda for dependency management in Ubuntu or WSL2 in Windows.

### Conda 
##### Install Miniconda

* Download the Miniconda installer from Miniconda — conda documentation , or by running:
    ```
    wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" 
    ```
* Run the installer by navigating to the download directory and running:
    ```
    bash Miniconda3-latest-Linux-x86_64.sh
    ```
* Follow through the prompts to install Miniconda.
* Say yes to the option to run conda init at the end of the installer.
* Close and reopen your terminal window after installing conda for it to recognise conda command
* By default, the version of python installed in the base conda environment will take precedence over the system python when simply running `python` in the shell. To disable this behaviour, and allow using the system python by default, unless you have specifically activated a conda environment, run:
    ```
    conda config --set auto_activate_base false
    ```
* Confirm the behaviour is as expected by running `which python` which should be `/usr/bin/python`. (You may need to reopen your terminal window after running the conda config command for it to take effect).
##### Create conda environment
* Create a new conda environment by running:
    ```
    conda env create -n schools_change_detection --file environment.yml
    ```

## schools_change_detection.py

### Help

```
usage: schools_change_detection.py [-h] -t {file,db} -i <STRING> [-o <PATH>]
                                   [--save-moe-api-response] [--moe-api-response <PATH>]
                                   [--compare <STRING>] [--overwrite] [--quiet]

Check for changes within the MoE schools data which need to be applied to the NZ Facilities data.

options:
  -h, --help            show this help message and exit
  -t {file,db}, --type {file,db}
                        Flag indicating whether the facilities source type is an OGR readable
                        file or a PostgreSQL DB. (default: None)
  -i <STRING>, --input <STRING>
                        If the facilities source type is 'file', then this should contain the
                        PATH to the source file (it must be an OGR readable format). If source
                        type is 'db', then this should contain a JSON formatted string containing
                        the values for these keys: name, host, port, user, password, schema,
                        table. (default: None)
  -o <PATH>, --output <PATH>
                        Output file location. Must be a valid path a file ending in .gpkg.
                        (default: /home/ajacombs/dev/nz-
                        facilities/schools_change_detection/schools_change_detection.gpkg)
  --save-moe-api-response
                        Save the response from the MOE API. Will save in the same directory as
                        the specified output file. (default: False)
  --moe-api-response <PATH>
                        Path to response from the MOE API saved from a previous run of this
                        script. If passed, this data will be used instead of querying the API.
                        Useful for testing. (default: None)
  --compare <STRING>    Comma separated list of attributes to compare on. Valid options are
                        source_name,source_type,source_id,occupancy (default:
                        source_type,source_name,source_id)
  --overwrite           Overwrite the specified output file if it already exists. (default:
                        False)
  --quiet               Do not print any logging messages to screen. (default: False)
```

### To execute

* Activate Conda environment:
    ```
    conda activate schools_change_detection
    ```

* To see available options, first run:
    ```
    python schools_change_detection.py --help
    ```

* To execute with NZ Facilities from a Geopackage:
    ```
    python schools_change_detection.py -t file -i <PATH> -o <PATH>
    ```

* To execute with NZ Facilities from a Database:
    ```
    python schools_change_detection.py -t db -i '{"name": "<database_name>", "host": "<host>", "port":"<port>", "user":"<username>", "password": "<password>", "schema": "<db schema>", "table":"<table name>"}'  -o <PATH>
    ```

* To execute without having the logging printed to screen:
    ```
    python schools_change_detection.py -t file -i <PATH> -o <PATH> --quiet
    ```

* To execute and automatically overwrite output direcotry:
    ```
    python schools_change_detection.py -t file -i <PATH> -o <PATH> --ovwerwrite
    ```