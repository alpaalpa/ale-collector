DBHOST=localhost
DBNAME=ale
PROGFILES=config.py ale-collector.py ale-reader.py analyse_ale_collector.py update_ale_collector_stats.py ale-playback.py ale-record.py
SUPPORTFILES=ale-psql.sql oui.txt schema.proto Makefile
LIB=ale_dbi.py ale_enums.py restapi.py oui.py ale_pprint.py
DOCS=README.md INSTALL.rst 

FILES=${PROGFILES} ${SUPPORTFILES} ${LIB} ${DOCS}

schema_pb2.py:schema.proto
	/usr/local/bin/protoc --python_out=. schema.proto

run: schema_pb2.py

initdb: ale-psql.sql schema_pb2.py
	 psql -h ${DBHOST} ${DBNAME} < ale-psql.sql

reallyinitdb: 
	dropdb ${DBNAME}
	createdb ${DBNAME}
	make initdb

ale-api.tar: ${PROGFILES} ${SUPPORTFILES} ${LIB} ${DOCS}
	tar cf ale-api.tar ${PROGFILES} ${SUPPORTFILES} ${LIB}
	
ale-api.tar.gz: ale-api.tar
	gzip ale-api.tar	
	
feed-reader: feed-reader.cc schema.pb.cc schema.pb.h
	g++ -I/usr/local/include -L/usr/local/lib -lprotobuf -lzmq -o feed-reader feed-reader.cc schema.pb.cc
	
schema.pb.cc schema.pb.h: schema.proto
	/usr/local/bin/protoc --cpp_out=. --python_out=. schema.proto

