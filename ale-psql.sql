DROP TABLE IF EXISTS Server;

CREATE TABLE Server (
	id SERIAL PRIMARY KEY,
	name TEXT,
	host TEXT NOT NULL,
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	UNIQUE (host)
);

DROP TABLE IF EXISTS Campus;
CREATE TABLE Campus (
	id SERIAL PRIMARY KEY,
	name TEXT NOT NULL,
	idFromAWMS TEXT NOT NULL,		-- Campus ID used in AirWave
	ALETimestamp TIMESTAMPTZ,	-- Timestamp as read from ALE REST API
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	server_id INTEGER REFERENCES Server(id),
	timezone TEXT,
	UNIQUE (idFromAWMS)
);
DROP INDEX IF EXISTS Campus_idx;
CREATE INDEX Campus_idx ON Campus(idFromAWMS);

DROP TABLE IF EXISTS Building;
CREATE TABLE Building (
	id SERIAL PRIMARY KEY,
	name TEXT NOT NULL,
	idFromAWMS TEXT NOT NULL,		-- Building ID used in AirWave
	campus_id INTEGER REFERENCES Campus(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	ALETimestamp TIMESTAMPTZ,	-- Timestamp as read from ALE REST API
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	UNIQUE (idFromAWMS)
);
CREATE INDEX Building_idx ON Building(idFromAWMS);

DROP TABLE IF EXISTS Floor;
CREATE TABLE Floor (
	id SERIAL PRIMARY KEY,
	name TEXT NOT NULL,
	idFromAWMS TEXT NOT NULL,		-- Floor ID used in AirWave
	latitude REAL,
	longitude REAL,
	img_path TEXT,
	img_width REAL,
	img_length REAL,
	building_id INTEGER REFERENCES Building(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	level REAL,
	units TEXT,
	grid_size REAL,
	ALETimestamp TIMESTAMPTZ,	-- Timestamp as read from ALE REST API
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	UNIQUE (idFromAWMS)
);
CREATE INDEX Floor_idx ON Floor(idFromAWMS);


DROP TABLE IF EXISTS Endpoint;
CREATE TABLE Endpoint (
	id SERIAL PRIMARY KEY,
	macAddress TEXT NOT NULL,
	isAssociated BOOLEAN, -- Whether the client is associated
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	lastHeardTime TIMESTAMPTZ, -- Time when this device was last detected by ALE
	lastHeardMessage TEXT, /* The last ALE message type that triggers this update. 
								E.g. location, presence, rssi, geofence_notify, etc	*/
	receiveNotification BOOLEAN DEFAULT FALSE, -- Whether endpoint will receive notification (Whether or not it is registered)
	appInstalled BOOLEAN DEFAULT NULL, -- Whether Meridian App (or equivalent such as AppViewer has been installed)
	lastNotificationAttempted TIMESTAMPTZ, -- When was the last notification 
	lastNotificationStatus INTEGER DEFAULT NULL, -- Status of last notification attempt
	maxRSSI INTEGER,	-- The maximum RSSI heard for this client.
	username TEXT,	-- The last authenticated username associated with thie endpoint
	role TEXT,
	bssid TEXT,
	devType TEXT,
	rtlsType INTEGER, -- Used by RTLS station report
	ip TEXT,
-- /*	lastHeardTimeRTLS TIMESTAMPTZ, /* The time of the last station report minus the 'age' */
	maxdBm INTEGER,
	lastChannel INTEGER, -- Last channel heard in an RTLS Staiton Report
	lastNoiseFloor INTEGER, -- Last noise floor heard in an RTLS Staiton Report
	lastAge INTEGER, -- The age field in the last RTLS Station Report
	lastRadioBSSID TEXT,
	lastMonBSSID TEXT,
	UNIQUE (macAddress)  
);
CREATE INDEX Endpoint_idx ON Endpoint(macAddress);

DROP TABLE IF EXISTS Location;
CREATE TABLE Location (
	/* This table keeps track of all historical location of an endpoint */
	id SERIAL PRIMARY KEY,
	endpoint_id INTEGER REFERENCES Endpoint(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	serverTimestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- Timestamp of the server
	ALETimestamp TIMESTAMPTZ,
	campus_id INTEGER REFERENCES Campus(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,	-- Use database's ID not AirWave's
	building_id INTEGER REFERENCES Building(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	floor_id INTEGER REFERENCES Floor(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	x REAL,	-- Unit is in whatever ALE sends us. 
	y REAL,  
	algorithm INTEGER	/* Which algorithm was used for this update. 
						AP_Placement = 1
		 				Triangulation = 0 */
);
CREATE INDEX Location_idx ON Location(endpoint_id);



DROP TABLE IF EXISTS Person;
CREATE TABLE Person (
	id SERIAL PRIMARY KEY,
	userID TEXT NOT NULL UNIQUE, -- AD: sAMAccountName
	email TEXT NOT NULL UNIQUE,	-- AD: userPrincipalName
	employeeNumber INTEGER, -- AD: employeeNumber
	firstName TEXT,	-- AD: givenName
	lastName TEXT,	-- AD: sn
	displayName TEXT,	-- AD: displayName
	company TEXT,	-- AD: company
	department TEXT, -- AD: department 
	title TEXT, -- AD: title
	mobile TEXT,
	country TEXT,	-- AD: c
	language TEXT,
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX Person_idx ON Person(userID,email);

DROP TABLE IF EXISTS Endpoint_Person;
CREATE TABLE Endpoint_Person (
    id SERIAL PRIMARY KEY,
    endpoint_id INTEGER REFERENCES Endpoint(id),
    person_id INTEGER REFERENCES Person(id),
    lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX Endpoint_Person_idx ON Endpoint_Person(endpoint_id);

DROP TABLE IF EXISTS Notification;
CREATE TABLE Notification (
    id SERIAL PRIMARY KEY,
    endpoint_id INTEGER REFERENCES Endpoint(id),
	sentStatus INTEGER,
	message TEXT, -- Notification content
    notificationSentTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX Notification_idx ON Notification(endpoint_id);

DROP TABLE IF EXISTS AP;
CREATE TABLE AP (
	id SERIAL PRIMARY KEY,
	macAddress TEXT NOT NULL UNIQUE,
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	ip TEXT,
	name TEXT,
	apGroup TEXT,
	model TEXT,
	mode INTEGER, -- IAP, CAP
	reboots INTEGER,
	rebootstraps INTEGER,
	server_id INTEGER REFERENCES Server(id)
);


DROP INDEX IF EXISTS AP_idx;
CREATE INDEX AP_idx ON AP(macAddress);

DROP TABLE IF EXISTS Radio_BSSID;
CREATE TABLE Radio_BSSID (
	id SERIAL PRIMARY KEY,
	radio_bssid TEXT NOT NULL UNIQUE,
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,	-- Timestamp when this record was last modified
	phyType INTEGER,
	ht INTEGER,
	mode INTEGER,
	ap_id INTEGER REFERENCES AP(id)
);
CREATE INDEX Radio_BSSID_idx ON Radio_BSSID(radio_bssid);

DROP TABLE IF EXISTS VAP;
CREATE TABLE IF NOT EXISTS VAP (
	id SERIAL PRIMARY KEY,
	bssid TEXT NOT NULL UNIQUE,
	essid TEXT,
	radio_id INTEGER REFERENCES Radio_BSSID(id),
	lastModifiedTime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP	-- Timestamp when this record was last modified
);
CREATE INDEX VAP_idx ON VAP(bssid);

DROP TABLE IF EXISTS Presence;
CREATE TABLE IF NOT EXISTS Presence (
	id SERIAL PRIMARY KEY,
	endpoint_id INTEGER REFERENCES Endpoint(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	serverTimestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- Timestamp of the server listening to ALE message
	ALETimestamp TIMESTAMPTZ, -- Timestamp of the message sent from ALE
	isAssociated BOOLEAN,
	rssi INTEGER,
	ap_name TEXT,
	radio_id INTEGER REFERENCES Radio_BSSID(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,	
	server_id INTEGER REFERENCES Server(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED	
	);
CREATE INDEX Presence_idx ON Presence(endpoint_id);

DROP TABLE IF EXISTS RSSI;
CREATE TABLE IF NOT EXISTS RSSI (
	id SERIAL PRIMARY KEY,
	endpoint_id INTEGER REFERENCES Endpoint(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
	serverTimestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- Timestamp of the server listening to ALE message
	ALETimestamp TIMESTAMPTZ, -- Timestamp of the message sent from ALE
	radio_id INTEGER REFERENCES Radio_BSSID(id)	ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
	rssi INTEGER,
	isAssociated BOOLEAN,
	age INTEGER,
	noise_floor INTEGER,
	assoc_bssid TEXT
);
CREATE INDEX RSSI_idx ON RSSI(endpoint_id);


DROP TABLE IF EXISTS Geofence_Notify;
CREATE TABLE Geofence_Notify (
	id SERIAL PRIMARY KEY,
	endpoint_id INTEGER REFERENCES Endpoint(id)
		ON DELETE RESTRICT
		DEFERRABLE INITIALLY DEFERRED,
	serverTimestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- Timestamp of the server listening to ALE message
	ALETimestamp TIMESTAMPTZ, -- Timestamp of the message sent from ALE
	geofenceName TEXT,
	apName TEXT,
	ap_id INTEGER REFERENCES AP(id),
	bssid TEXT,
	rssi INTEGER
);
CREATE INDEX Geofence_Notify_idx ON Geofence_Notify(endpoint_id);


DROP TABLE IF EXISTS Location_Statistics;
CREATE TABLE Location_Statistics (
	id SERIAL PRIMARY KEY,
	serverTimestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
	startTime TIMESTAMPTZ, -- Startime of the stats
	interval INTEGER,	-- interval is expressed in seconds
	type INTEGER,  -- 0 campus, 1 - building, 2 - floor
	location_id INTEGER, -- either campus_id, building_id, floor_id
	value INTEGER
);


