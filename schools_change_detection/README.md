# Schools Change Detection

Scripts for checking the MOE Schools data against NZ Facilities data to identify updates needed.
Returns a geopackage containing information about updates, deletions and additions needed.

## Before you begin

This script is best executed in Ubuntu or using WSL2 in Windows using Conda for dependency management.  

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
* By default, the version of python installed in the base conda environment will take precedence over the system python when simply running python3 in the shell. To disable this behaviour, and allow using the system python by default, unless you have specifically activated a conda environment, run:
    ```
    conda config --set auto_activate_base false
    ```
* Confirm the behaviour is as expected by running which python3 which should be /usr/bin/python3. (You may need to reopen your terminal window after running the conda config command for it to take effect).
##### Create conda environment
* Create a new conda environment by running:
    ```
    conda env create -n schools_change_detection --file environment.yml
    ```

#### Dependencies

* Python 3.10
* Pyproj 3.4
* Psycopg2
* Fiona 1.9
* Shapely 2.0.*
* Tqdm 4.*
* Requests
* Copy

### TLDR

```
usage: schools_change_detection.py [-h] -t {file,db} -i <STRING> -o <PATH> [--overwrite] [--quiet]

Check for changes within the MoE schools data which need to be applied to the NZ Facilities data.

options:
  -h, --help            show this help message and exit
  -t {file,db}, --type {file,db}
                        Flag indicating whether the facilities source type is an OGR readable file or a PostgreSQL DB (default: None)
  -i <STRING>, --input <STRING>
                        If the facilties source type is 'file', then this should contain the PATH to the source file (it must be an OGR readable format). If source type is 'db', then this should contain a JSON
                        formatted string containing the values for these keys: name, host, port, user, password, schema, table. (default: None)
  -o <PATH>, --output <PATH>
                        Output directory which source files will be copied to and final reports outputted to. (default: /mnt/c/dev/nz-facilities/schools_change_detection/output)
  --overwrite           Overwrite the specified output file if it already exists. (default: False)
  --quiet               Do not print any logging messages to screen. (default: False)
```

#### To execute

* Activate Conda environment:
    ```
    conda activate schools_change_detection
    ```

* To see available options, first run:
    ```
    python3 /path/to/script/schools_change_detection.py --help
    ```

* To execute with NZ Facilities from a Geopackage:
    ```
    python3 /path/to/script/attribute_checker.py -t file -i <PATH> -o <PATH>
    ```

* To execute with NZ Faclities from a Database:
    ```
    python3 /path/to/script/attribute_checker.py -t db -i -i '{"name": "<database_name>", "host": "<host>", "port":"<port>", "user":"<username>", "password": "<password>", "schema": "<db schema>", "table":"<table name>"}'  -o <PATH>
    ```

* To execute without having the logging printed to screen:
    ```
    python3 /path/to/script/attribute_checker.py -t file -i <PATH> -o <PATH> --quiet
    ```

* To execute and automatically overwrite output direcotry:
    ```
    python3 /path/to/script/attribute_checker.py -t file -i <PATH> -o <PATH> --ovwerwrite
    ```

* The default directory for the log file is the current working directory. Specify an alternative destination by:
    ```
    python3 /path/to/script/attribute_checker.py <PATH> --logfile <PATH TO LOGFILE>
    ```
