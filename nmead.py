#!/usr/bin/python

from daemon import Daemon
import sys, os
import bluetooth
import time
import logging
import Pyro4

#MAINREP = "/home/djo/Bureau/dumpDaemon/dump/"
MAINREP = "/root/nmea/"
BUFFER_SIZE = 1024
UUID = "f1e7facd-6bf2-4dd0-b96f-5ea70c475c48"
MAC = "D8:B3:77:27:D7:45"
SampleRate = 10

DEBUG = False
timeSet = False
LastTimestampAltitude = 0
LastTimestampPosition = 0
proxy = None

def timeToMakeSample(timestamp, last):
    if len(timestamp) != 6:
        logging.warning("invalid time length : "+timestamp)
        return False
        
    try:
        hour   = int(timestamp[0:2])
        minute = int(timestamp[2:4])
        second = int(timestamp[4:])
    except ValueError as ve:
        logging.exception("invalid time : "+str(ve))
        return False
        
    currentTimestamp = second + (minute*60) + (hour * 3600)    
    return currentTimestamp,(last < (currentTimestamp - SampleRate))

#GPRMC, GPGGA, GPGLL
#nmea_obj.lat nmea_obj.lat_dir nmea_obj.lon nmea_obj.lon_dir nmea_obj.timestamp
def setPosition(nmea_obj):
    global proxy,LastTimestampPosition
    newTime,needToUpdate = timeToMakeSample(nmea_obj.timestamp, LastTimestampPosition)
    position = nmea_obj.lat+nmea_obj.lat_dir+" "+nmea_obj.lon+nmea_obj.lon_dir+", fix time : "+nmea_obj.timestamp
    if needToUpdate:
        LastTimestampPosition = newTime
        logging.info("position : "+position)
        
        try:
            if proxy == None:
                proxy=Pyro4.Proxy("PYRONAME:dump.gpsdata")
                
            proxy.setPosition(position)
            logging.info
            
        except Exception as ex:
            proxy = None
            logging.exception("Pyro4 Exception (setPosition) : "+str(ex))
    else:
        logging.info("position (not new) : "+position)
            
#GPGGA
#gpgga.antenna_altitude, gpgga.altitude_units, gpgga.timestamp        
def setAltitude(gpgga):
    global proxy, LastTimestampAltitude
    newTime,needToUpdate = timeToMakeSample(gpgga.timestamp, LastTimestampAltitude)
    #TODO replace gpgga.timestamp with newTime, and add date
    altitude = gpgga.antenna_altitude+" "+gpgga.altitude_units+", fix time : "+gpgga.timestamp

    if needToUpdate:
        LastTimestampAltitude = newTime
        logging.info("altitude : "+altitude)
        
        try:
            if proxy == None:
                proxy=Pyro4.Proxy("PYRONAME:dump.gpsdata")

            proxy.setAltitude(altitude)

        except Exception as ex:
            proxy = None
            logging.exception("Pyro4 Exception (setAltitude) : "+str(ex))
    else:
        logging.info("altitude (not new) : "+altitude)

def setTime(gpzda):
    global timeSet
    
    if timeSet:
        return
    
    month = ""
    if gpzda.month == "01":
        month = "JAN"
    elif gpzda.month == "02":
        month = "FEB"
    elif gpzda.month == "03":
        month = "MAR"
    elif gpzda.month == "04":
        month = "APR"
    elif gpzda.month == "05":
        month = "MAY"
    elif gpzda.month == "06":
        month = "JUN"
    elif gpzda.month == "07":
        month = "JUL"
    elif gpzda.month == "08":
        month = "AUG"
    elif gpzda.month == "09":
        month = "SEP"
    elif gpzda.month == "10":
        month = "OCT"
    elif gpzda.month == "11":
        month = "NOV"
    elif gpzda.month == "12":
        month = "DEC"
    else:
        logging.warning("unknown month in gpzda obj : "+gpzda.month)
        return
    
    if len(gpzda.timestamp) != 9:
        logging.warning("invalid time length : "+gpzda.timestamp)
        return
    if not timeSet:
        newDate = "date -s \""+str(gpzda.day)+" "+month+" "+gpzda.year+" "+gpzda.timestamp[0:2]+":"+gpzda.timestamp[2:4]+":"+gpzda.timestamp[4:6]+"\""
        logging.info(newDate)
	#TODO BUG shit... forget to uncomment...
        #TODO if os.system(newDate) != 0:
        #    logging.warning("failed to set date : "+newDate)
        timeSet = True

class MyDaemon(Daemon.Daemon):
    def run(self):
        #if DEBUG:
        #    logging.basicConfig(format='%(asctime)s %(message)s')
        #else:    
        logging.basicConfig(format='%(asctime)s %(message)s', filename=MAINREP+'log/nmeareceiver'+str(os.getpid())+'.log',level=logging.DEBUG)        
        logging.info("nmead start")
        
        while True:
            #find the service
            try: 
                service_matches = bluetooth.find_service(address = MAC, uuid = UUID )
            
                if len(service_matches) == 0:
                    logging.warning("no service found")
                    time.sleep(2)#wait 2 seconds
                    continue #and try again
            except Exception as ex:
                logging.exception("looking service Exception : "+str(cte))
                time.sleep(2)
                continue
            logging.info("service found !!!")
            #connect to the service
            try:
                #connect to the device
                sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
                sock.connect((service_matches[0]["host"], service_matches[0]["port"]))
            except Exception as ex:
                logging.exception("Connection Exception : "+str(ex))
                time.sleep(2)
                continue
            
            try:
                logging.info("connected to client : "+str(sock))
            
                previousData = ""
                while True:#receive nmea frame
                    data = previousData + sock.recv(1024) #return a string
                    previousData = ""
                    
                    split_data = data.split("$")

                    for i in range(0,len(split_data)):
                        string = split_data[i]

                        #empty string ?
                        if len(string) == 0:
                            #if the string is empty and is the last
                            if i == len(split_data)-1:
                                break

                            #invalid data, if not the last string, ignore it    
                            continue

                        #end with newline ?
                        if string[-1] != "\n":
                            #last item ?
                            if i == len(split_data)-1:
                                previousData = string
                                break

                            #invalid data, if not the last string, ignore it
                            continue

                        #this string begins with a $ and ends with a newline
                        string = string[:-1] #remove the newline, the $ is already removed with split

                        #TODO remove other incorect caracters
                            #computation with checksum? see streamer _split method
                            #usefull?

                        #Find the type of nmea data
                        nmea_type = string.split(',')[0] #un split sur une chaine valide retourne toujours au moins un item

                        try: #load module with the wanted class
                            sen_mod = __import__('pynmea.nmea', fromlist=[nmea_type])
                        except TypeError as te:
                            logging.exception("failed to load nmea module with type <"+str(nmea_type)+"> : "+str(te))
                            continue

                        try: #instanciate the class 
                            nmea_ob = getattr(sen_mod, nmea_type)()
                        except AttributeError as ae:
                            logging.exception("unknown nmea type <"+str(nmea_type)+"> : "+str(ae))
                            continue

                        #parse it
                        nmea_ob.parse(string)#TODO how to manage parsing error???
                        #logging.info("string received : "+str(string))
                        #make traitment with data
                        if "GPRMC" == nmea_type or "GPGLL" == nmea_type:
                            setPosition(nmea_ob)
                        elif "GPGGA" == nmea_type:
                            setAltitude(nmea_ob)
                            setPosition(nmea_ob)
                        elif "GPZDA" == nmea_type:
                            setTime(nmea_ob)
                        else:
                            logging.warning("unused nmea obj : "+nmea_type)
                    
            except Exception as ex:
                logging.exception("manage data Exception : "+str(ex))
                time.sleep(2)
                continue

if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-nmeareceiver.pid')
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
