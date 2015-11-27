#Installing ale-collector 


The ALE Collector is a python scripts that subscribe to the feed from Aruba ALE and store in a db.

It requires packages and python modules that might not be pre-installed on the *NIX system.

1. python 2.7

ALE Collector will run with python 2.6.x.  But some logging functions does not work properly.
For best results and compatibility, please install python2.7.

2. Google Protobuf

     https://code.google.com/p/protobuf/
     download
     cd protobuf-2.x.x
          ./configure
          make
          make check
          sudo make install
 * To install python-protobuf
     cd python          
     python setup.py build
     python setup.py test
     sudo python setup.py install
	 
3. Install ZMQ

     http://zeromq.org
     Download source: http://zeromq.org/area:download
         cd zeromq-4.0.x/
          ./configure
          make
          make check
          sudo make install
		  
4. Python installer

* Install python-devel package

 yum install python-devel

* setuptools

 Let's download the installation file using wget:

	wget --no-check-certificate https://pypi.python.org/packages/source/s/setuptools/setuptools-1.4.2.tar.gz

 Extract the files from the archive:

	tar -xvf setuptools-1.4.2.tar.gz

 Enter the extracted directory:

	cd setuptools-1.4.2

 Install setuptools using the Python

	sudo python setup.py install

* PIP

	curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | sudo python

* Install pyzmq 

	zeromq (depends on python-devel)
     sudo pip install pyzmq
	 
* Install 'requests'

     sudo pip install requests

 * Install 'netaddr'

     sudo pip install netaddr	 

5. Install/Config PostgreSQL	 
	 
6. Initialise Database

	psql -h <PostgreSQL Hostname/IP> <database name> < ale-psql.sql

7. Take a look at the customizable configurations in:

	config.py
	

		   

	 
