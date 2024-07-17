# NZ Facilities change detection

A CLI application which enables comparing NZ Facilities data against source data
to identify any changes.

The application has a collection of commands, implementing change detection
for school facilities (comparing against data from the Ministry of Education),
and for healthcare facilities (comparing against data from the Ministry of Health
and te Whatu Ora).


## Installation

This script is best executed using Conda for dependency management in Ubuntu or WSL2 in Windows.

### Install Miniconda

- Download the [Miniconda installer](https://docs.anaconda.com/free/miniconda/) 
  from their website, or by running:
  ```
  wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
  ```
- Run the installer by navigating to the download directory and running:
  ```
  bash Miniconda3-latest-Linux-x86_64.sh
  ```
- Follow through the prompts to install Miniconda.
- Say yes to the option to run `conda init` at the end of the installer.
- Close and reopen your terminal window after installing conda for it to
  recognise conda command
- By default, the version of python installed in the base conda environment will
  take precedence over the system python when simply running `python` in the
  shell. To disable this behaviour, and allow using the system python by
  default, unless you have specifically activated a conda environment, run:
    ```
    conda config --set auto_activate_base false
    ```
- Confirm the behaviour is as expected by running `which python` which should be
  `/usr/bin/python`. (You may need to reopen your terminal window after running
  the conda config command for it to take effect).

### Create conda environment

- Create a new conda environment by running [from this directory]:
  ```
  conda env create -f environment.yml
  ```

### Activate conda environment

- Activate the conda environment:
  ```
  conda activate facilities-change-detection
  ```

### Install CLI application in conda environment

- Install the CLI application in the conda environment by running [from this
  directory]:
  ```
  pip install --editable .
  ```
- This installs a command named `facilities-change-detection`, which can be run
  from any directory (whenever the conda environment is activated).


## Running the application

To run the application, first activate the conda environment with
`conda activate facilities-change-detection`, then run the command
`facilities-change-detection`.

The available commands can be listed with `facilities-change-detection --help`,
with some commands having subcommands. Help text is avilable for each command,
which describes the arguments it takes, e.g.
`facilities-change-detection hospitals compare --help`