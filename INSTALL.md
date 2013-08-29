Installation
============

This document describes the installation of the `viveur` software package on an
Ubuntu 13.04 installation.

Required Software
-----------------

- python2.7 (this is default) and the dev headers (apt-get install python-dev)
- libxml2 dev headers (apt-get install libxml2-dev libxslt1-dev)
- Apache Ant (1.8 or higher) (apt-get install ant)
- MySQL 5.1 (or higher) (apt-get install mysql-client mysql-server)

- Oracle Java 6 SDK (it needs to be this specific version)
  You will need to download this from Oracle, then use update-alternatives to register
  (google for a howto)
- Oracle InstantClient
  You will need to download this from Oracle, and manual install (in /opt/ or somewhere else)

Setuptools
----------

The version of setuptools that comes with Ubuntu is probably lower then version 0.7.
You can try to work around this by using `virtualenv --no-setuptools`,
but there can still be issues finding dependencies.
I suggest updating the
systemwide setuptools version using the command:

   sudo pip install -U distribute

If pip is not installed on the system you can do an `apt-get install python-pip`

Configuring MySQL
-----------------
Create a database for the vivo content.
The username, password and database name should be entered in the [config] section
of the buildout.cfg file.

CREATE DATABASE vivo CHARACTER SET utf8;
GRANT ALL ON vivo.* TO 'vivo'@'localhost' IDENTIFIED BY 'password';

Configure Oracle Instantclient
------------------------------

Not much to do here, but you must export the paths to Oracle instantclient
otherwise the software will fail to connect.
You might want to put the lines below in your .bashrc profile

export ORACLE_HOME=/opt/oracle/instantclient_11_2
export LD_LIBRARY_PATH=/opt/oracle/instantclient_11_2

Installing the Viveur Software
------------------------------

The software itself can be downloaded from github.
It uses buildout to download download and configure tomcat/vivo
Issue the following commands:

$ git clone http://github.com/jascoul/viveur
$ cd viveur
$ mv buildout.cfg.in buildout.cfg

Now edit the [config] and [metis] section of the buildout.cfg file
Also be sure to export the Oracle path as described in `Configure Oracle Instantclient`

Next we create the python environment where the software will be installed

$ python bootstrap.py

In the last and final step all dependencies will be downloaded/installed.
This will take some time as it will compile cython/lxml and configure vivo with ant

$ ./bin/buildout

For more information on how to use the software see the `USAGE` file
