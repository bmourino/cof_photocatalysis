# AiiDA plugin to evaluate COFs for photocatalysis

# Installation information
This plugin requires the aiida-lsmo plugin, which is still not updated to the latest version of AiiDA. Therefore, it is important to follow the specific installation for AiiDA~v1.6. You can follow the [aiida instalation web page](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/get_started.html). 
However, here we provide information on how to do it to avoid incompatibility errors. This can happen with, for example, RabbitMQ (this is fixed for later versions of AiiDA).

# Conda environment and installing aiida-core
We recommend creating an environment with python=3.7:

    $ conda create -n aiida1.6 conda-forge -c aiida-core=1.6 python=3.7

or for a quicker installation (install mamba with conda install -c conda-forge mamba):

    $ mamba create --name "aiida_test" python=3.7
    $ mamba install -y --name "aiida_test" -c conda-forge aiida-core=1.6

then:
    $ conda activate aiida_test
    $ reentry scan

# Installing AiiDA services
PostgreSQL can be installed normally:

    $ sudo apt install postgresql postgresql-server-dev-all postgresql-client

For this version of AiiDA, RabbitMQ version should be < 3.7. Here we use [docker](https://docs.docker.com/engine/install/) to specify a version and a different port (in case you already have a server running in a system-wide installation):

    $ sudo docker-compose -f setup/cofs-docker-compose.yml up -d

# Initializing the servers and setting up a profile
Refer to [aiida advanced configuration](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/installation.html) to create a database.

*TIP*
If you don't want to have to change anything on the yaml file, just do the following to setup a postgres database:

    $ sudo su - postgres 
    $ psql
    $ CREATE USER test WITH PASSWORD 'test';
    $ CREATE DATABASE testdb OWNER test ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;
    $ GRANT ALL PRIVILEGES ON DATABASE testdb to test;
    $ \q
    $ exit

And to test:

    $ psql -h localhost -d testdb -U test -W

We provide a yaml file (setup/profile.yaml) as an example to set up a profile. You should change your contact information, as well as username and password for the database. You can change other information too, but make sure to keep the broker port (5673 in this case) the same as specified in the docker-compose file.

You can set up the profile as follows:

    $ verdi setup --config setup/profile.yaml

Test if everything worked with:

    $ verdi status

Read the aiida [how-to guides](https://aiida.readthedocs.io/projects/aiida-core/en/latest/howto/index.html) for tips on how to setup a computer and code, how to run calculations and workflows etc.

# Installing aiida-lsmo and our plugin

Proceed with the following:

    $ git clone https://github.com/lsmo-epfl/aiida-lsmo
    $ cd aiida-lsmo
    $ pip install -e .
    $ reentry scan

Then:

    $ git clone https://github.com/bmourino/cof_photocatalysis.git
    $ cd cofs_photocatalysis
    $ pip install -e .
    $ reentry scan

To check if installed properly, when running the following line you should get the helper for the Cp2kPhotoCatWorkChain: #todo: clean workchain

    $ verdi plugin list aiida.workflows photocat_workchains.cp2k_photocat

# Usage

An example of run file can be found at in the run folder, and you can run it with:

    $ verdi run run_photocat_builder_std.py

Currently the workchain performs optimization and band structure calculations. Electron and hole injection must be performed separately, and in the run folder there are some examples. #todo: update examples

# Post processing of results

In the folder scripts you can find examples of jupyter notebooks to plot band structure and obtain effective masses; perform band alignment; get electron and hole injection. 

Both band alignment and electron and hole injection can take time, and we offer the possibility to perform it with aiida calculations in a cluster. #todo: explain usage, and how to setup a python environment in cscs clusters

