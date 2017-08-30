#!/bin/bash

cd /sites/destinyloadouts/scripts

DBHOST="XXXXXXXXXXXXX.XXXXXXXXXXXX.us-east-1.rds.amazonaws.com"
DBNAME="postgres"
DBUSER="XXXXXXXXXXXXX"
DBPASS="XXXXXXXXXXXXX"
DBPORT="5432"

echo "$DBHOST:$DBPORT:$DBNAME:$DBUSER:$DBPASS" > ~/.pgpass
chmod 0600 ~/.pgpass

BOOTSTRAP_SQL_FILE="bootstrap-db.sql"

/usr/bin/psql -w -h "$DBHOST" -p "$DBPORT" -U "$DBUSER" -d "$DBNAME" -f "$BOOTSTRAP_SQL_FILE"

exit $?

