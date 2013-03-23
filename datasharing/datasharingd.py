#!/usr/bin/python

import logging, os, time, sys
from daemon import Daemon
import Pyro4

#MAINREP = "/home/djo/Bureau/dumpDaemon/dump/"
MAINREP = "/root/datasharing/"

class GpsData(object):
    def __init__(self):
        self.position = "unknown"
        self.altitude = "unknown"
        
    def setAltitude(self,altitude):
        self.altitude = altitude
        
    def setPosition(self,position):
        self.position = position
        
    def getAltitude(self):
        return self.altitude
        
    def getPosition(self):
        return self.position

class MyDaemon(Daemon.Daemon):
    def run(self):
        logging.basicConfig(format='%(asctime)s %(message)s', filename=MAINREP+'log/sharingDaemon'+str(os.getpid())+'.log',level=logging.DEBUG)
        while True:
            try:
                gpsdata=GpsData()

                daemon=Pyro4.Daemon()                 # make a Pyro daemon
                ns=Pyro4.locateNS()                   # find the name server
                uri=daemon.register(gpsdata)   # register the greeting object as a Pyro object
                ns.register("dump.gpsdata", uri)  # register the object with a name in the name server

                logging.info("Ready.")
                daemon.requestLoop()                  # start the event loop of the server to wait for calls
            except Exception as ex:
                logging.exception("dump exception : "+str(ex))
                time.sleep(2)


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-datasharing.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
	elif 'test' == sys.argv[1]:
            daemon.run()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)