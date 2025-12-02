# NZ Facilities change detection

A CLI application which enables comparing NZ Facilities data against source data
to identify any changes.

The application has a collection of commands, implementing change detection
for school facilities (comparing against data from the Ministry of Education),
and for healthcare facilities (comparing against data from the Ministry of Health
and te Whatu Ora).


## Installation

This script is best executed using Conda for dependency management in Ubuntu or WSL2 in Windows.

### Install Conda

- LINZ uses Miniforge, a minimal and open-source version of Conda that uses the community-driven conda-forge repository, https://github.com/conda-forge/miniforge.
- LINZ internal documentation for installing Miniforge: https://toitutewhenua.atlassian.net/wiki/spaces/TOP/pages/1585283478/Conda+Installation.

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