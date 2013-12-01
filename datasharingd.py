#!/usr/bin/python

import logging, os, time, sys
from daemon import Daemon
import Pyro4

#MAINREP = "/home/djo/Bureau/dumpDaemon/dump/"
MAINREP = "/root/datasharing/"

def getLogNextId():
    return len([name for name in os.listdir(MAINREP+"log/") if os.path.isfile(MAINREP+"log/"+name)])

class GpsData(object):
    def __init__(self):
        self.position = "0000.0000N 00000.0000E, fix time : 000000"
        self.altitude = "0.0 M, fix time : 000000"
        self.gpsLogId = -1
        
    def setAltitude(self,altitude):
        self.altitude = altitude
        
    def setPosition(self,position):
        self.position = position
        
    def getAltitude(self):
        return self.altitude
        
    def getPosition(self):
        return self.position

    def getGpsLogId(self):
        return self.gpsLogId

    def setGpsLogId(self,gpsLogId):
        self.gpsLogId = gpsLogId

class MyDaemon(Daemon.Daemon):
    def run(self):
        logging.basicConfig(format='%(asctime)s %(message)s', filename=MAINREP+'log/sharingDaemon_'+str(getLogNextId())+"_"+str(os.getpid())+'.log',level=logging.DEBUG)
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
