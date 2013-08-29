Starting The VIVO Server
------------------------

The VIVO software runs under Tomcat and can be started with the catalina script.
To make this a bit more manageable the buildout created some supervisor scripts in the
bin folder.

You can start Tomcat (and possibly other long running tasks) with the command:


$ ./bin/supervisord

This will start the supervisor daemon in the background. It will also start VIVO/Tomcat

With the command

$ ./bin/supervisorctl

You can manage the processes (start/stop/restart/tail logs, etc)

Ingesting Data into VIVO
------------------------

At the moment, the ingest script in the bin directory (`./bin/vivo_ingester`) is not finished.
If you have ingested data into VIVO that you want to remove, execute the following commands:

$ ./bin/drop_vivo_tables
$ rm -rf parts
$ ./bin/buildout

This will get you a clean environment.
Next you need to (re)start the VIVO server with the command:

$ ./bin/supervisorctl
$ restart Vivo

You can then visit the VIVO site for the first time, by going to:

http://localhost:8080/vivo

This can take a long time as VIVO is being configured/deployed in Tomcat.
You can then login as admin and upload the vivo.xml RDF file.

Generating VIVO RDF from the Metis DB
-------------------------------------

In the bin folder is a script called `./bin/metis_dumper`.
This script will connect to an Oracle Metis db (as configured in the buildout.cfg).
Transform the Metis data into an intermediate format, and transform
that into RDF using the BIBO/VIVO Ontology. It will then write out a file called vivo.xml.

The intermediate format with the Metis data from the DB. Is written to a file called `metis.pickle`. If the script finds a file with that name in the viveur directory. It will load the data from that cached file instead of querying the database.
This can be useful when you don't have access to the Metis DB, it also speeds things up a little bit.

The final result is an RDFXML file called vivo.xml. This can be ingested into VIVO as described in the step `Ingesting Data into VIVO`.
You can easily transform the RDFXML file into other formats using the `rapper` tool
(apt-get install raptor-utils):

$ rapper -i rdfxml vivo.xml -o turtle > vivo.ttl






Vivo runs under supervisor daemon. Start the daemon with:

./bin/supervisord

Restart / check status with

./bin/supervisorctl

