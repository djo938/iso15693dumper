from daemon import Daemon
import logging
import Pyro4
from gps import *
from gps.misc import *
import datetime, os

MAINREP = "/root/gpspyt/"
DEBUG = False
proxy = None
gpsd = None #seting the global variable
nextId = -1

def getLogNextId():
    return len([name for name in os.listdir(MAINREP+"log/") if os.path.isfile(MAINREP+"log/"+name)])

class MyDaemon(Daemon.Daemon):
    def run(self):
        global nextId
        
        nextId = getLogNextId()
        if DEBUG:
            logging.basicConfig(format='%(asctime)s %(message)s',level=logging.DEBUG)
        else:    
            logging.basicConfig(format='%(asctime)s %(message)s', filename=MAINREP+'log/gpsclid_'+str(nextId)+"_"+str(os.getpid())+'.log',level=logging.INFO)        
        logging.info("gps client start, log id : "+str(nextId))
        
        while True:
            try:
                gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
                proxy=Pyro4.Proxy("PYRONAME:dump.gpsdata")
                timeSet = False
                proxy.setGpsLogId(nextId)
                while True:
                    gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
                    
                    #generate fixTime
                    fixtime = "000000"
                    utcdatetime = None
                    if gpsd.utc != None and not isnan(gpsd.utc) and len(gpsd.utc) > 0:
                        utcfloatTime = isotime(gpsd.utc)
                        utcdatetime = datetime.datetime.fromtimestamp(int(utcfloatTime))
                        fixtime = "%.2d%.2d%.2d"%(utcdatetime.hour,utcdatetime.minute,utcdatetime.second)
                    
                    #set position
                    #Position : 4523.3998N 00637.7478E, fix time : 100100
                    #position = nmea_obj.lat+nmea_obj.lat_dir+" "+nmea_obj.lon+nmea_obj.lon_dir+", fix time : "+nmea_obj.timestamp
                    if not isnan(gpsd.fix.latitude) and not isnan(gpsd.fix.longitude):
                        position = str(gpsd.fix.latitude)+" "+str(gpsd.fix.longitude)+", fix time : "+fixtime
                        proxy.setPosition(position) 
                        logging.info("position : "+position)
                    
                    #set altitude
                    #Altitude : 2142.300048828125 M, fix time : 100100
                    #altitude = gpgga.antenna_altitude+" "+gpgga.altitude_units+", fix time : "+gpgga.timestamp
                    if not isnan(gpsd.fix.altitude):
                        altitude = str(gpsd.fix.altitude)+" M, fix time : "+fixtime
                        proxy.setAltitude(altitude)
                        logging.info("altitude : "+altitude)
                    
                    #sset time
                    if not timeSet and utcdatetime != None:
                        newDate = "date -s \""+str(utcdatetime.day)+" "+utcdatetime.strftime("%b")+" "+str(utcdatetime.year)+" "+fixtime[0:2]+":"+fixtime[2:4]+":"+fixtime[4:6]+"\""
                        logging.info(newDate)
                        if os.system(newDate) != 0:
                            logging.warning("failed to set date : "+newDate)
                        else:
                            timeSet = True
                    logging.info("datetime : "+str(utcdatetime))
                    
            except Exception as ex:
                logging.exception("manage data Exception : "+str(ex))
                time.sleep(2)
                continue

if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-gpscli.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'test' == sys.argv[1]:
            DEBUG = True
            daemon.run()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart|test" % sys.argv[0]
        sys.exit(2)