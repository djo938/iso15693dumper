#!/usr/bin/python

import logging, os, sys, time, datetime
from pydaemon import Daemon, getLogNextId
import Pyro4
from pysharegps import sharedGpsClient
from dumpformat import dump, dumpManager, byteListToString, saveDump
from data import owners

MAINREP = "/root/data/dump/"
SHORT_DURATION = 0x64
LONG_DURATION  = 0xff

def errorBeep(con,code):
    duration1 = duration2 = duration3 = SHORT_DURATION
    waiting1 = waiting2 = 0.2
    
    if code >= 7 or code < 0:
        duration1 = duration2 = duration3 = LONG_DURATION
        waiting1 = waiting2 = 0.5
    else:
        if (code&0x01) != 0:
            duration1 = LONG_DURATION
            waiting1 = 0.5
            
        if (code&0x02) != 0:
            duration2 = LONG_DURATION
            waiting2 = 0.5
            
        if (code&0x04) != 0:
            duration3 = LONG_DURATION
            
    con.transmit( [0xFF, 0xF0, 0x00, 0x00,0x03,0x1C,0x00,duration1,0x00] )
    time.sleep(waiting1)
    con.transmit( [0xFF, 0xF0, 0x00, 0x00,0x03,0x1C,0x00,duration2,0x00] )
    time.sleep(waiting2)
    con.transmit( [0xFF, 0xF0, 0x00, 0x00,0x03,0x1C,0x00,duration3,0x00] )


def dumpSkipass(con, currentDump, path):
    #first beep
    con.transmit( [0xff,0xf0,0x0,0x0,0x3,0x1c,0x0,0x82,0x0])

    #read UID
    uid, sw1, sw2 = con.transmit( [0xFF, 0xCA, 0x00, 0x00,0x00] )

    if sw1 != 0x90 and sw2 != 0x00:
        logging.error("failed to get UID with command [0xFF, 0xCA, 0x00, 0x00,0x00], get the following sw : %02X %02X"%(sw1, sw2))
        return

    currentDump.setUID(uid)
    logging.info("card uid : "+byteListToString(uid,":"))

    #compute UID and decimal UID
    uid_type = (uid[0] << 16) + (uid[1] << 8) + uid[2]

    uid_dec = 0
    for i in range(0,len(uid)):
        uid_dec += (uid[len(uid)-i-1]<<(i*8))

    uid.reverse()

    #read pix
    data, sw1, sw2 = con.transmit( [0xFF, 0xCA, 0xF1, 0x00, 0x00])

    if sw1 != 0x90 and sw2 != 0x00:
        logging.error("failed to get PIX with command [0xFF, 0xCA, 0xF1, 0x00, 0x00], get the following sw : %02X %02X"%(sw1, sw2))
        return

    #compute pix.NN and pix.SS    
    SS = data[0]
    NN = (data[1] << 8) + data[2]

    currentDump.setPIX(NN,SS)
    
    currentDataGroup = currentDump.getDataGroup()
    #prepare read data instruction
    if uid_type == 0xE01604 or uid_type == 0xE01694:
        # MultiReadBloc
        ins_prefix = [0xFF, 0xFE, 0x04, 0x0B, 0X0C, 0x60, 0x23]
        ins_prefix.extend(uid)
        ins_prefix.extend([0x00, 0x00])
        index_to_index = len(ins_prefix) - 2
        currentDump.setExtraInformation("readType", "MULTI READ")
    else:
        #single read bloc
        ins_prefix = [0xFF, 0xFE, 0x04, 0x0B, 0X0B, 0x60, 0x20]
        ins_prefix.extend(uid)
        ins_prefix.append(0x00)
        index_to_index = len(ins_prefix) - 1
        currentDump.setExtraInformation("readType", "SINGLE READ")

    #read all block
    for i in rangeToRead:
        ins_prefix[index_to_index] = i
        data, sw1, sw2 = con.transmit(ins_prefix)

        #end of stream?
        if (sw1 == 0x6F and sw2 == 0x2C) or (sw1 == 0x6F and sw2 == 0x27):
            currentDump.setExtraInformation("EndOfStream", "on sector "+str(i))
            break

        sect = "%02x"%i
        #read error?
        if sw1 != 0x90 or sw2 != 0x00:
            logging.error("failed to get read sector "+sect+" with command ["+byteListToString(ins_prefix)+"], get the following sw : %02X %02X"%(sw1, sw2))
            break

        #empty data?
        if data == None or len(data) == 0:
            currentDataGroup.addDataSector(i, data)
            break

        #new data available
        currentDataGroup.addDataSector(i, data[1:])
        if   data[0] == 0x00:
            currentDataGroup.addMisc(i, "Unlocked") #XXX bof bof de mettre ça dans le misc
            #f.write("sector "+sect+": "+byteListToString(data[1:],":")+" (Unlocked)\n")
        elif data[0] == 0x01:
            currentDataGroup.addMisc(i, "Locked") #XXX bof bof de mettre ça dans le misc
            #f.write("sector "+sect+": "+byteListToString(data[1:],":")+" (Locked)\n")
        else:
            currentDataGroup.addMisc(i, "Unknow "+str(data[0])) #XXX bof bof de mettre ça dans le misc
            #f.write("sector "+sect+": "+byteListToString(data,":")+"\n")

    #BEEP BEEP BEEEP
    errorBeep(con,0)
 
class MyDaemon(Daemon.Daemon):
    def run(self):
        #init gpsProxy
        gpsProxy = sharedGpsClient()
        
        ### INIT SMARTCARD ###
        
        while True: #sometime, pcscd take time to start
            try:
                from smartcard.CardType import AnyCardType
                from smartcard.CardRequest import CardRequest
                from smartcard.scard import INFINITE
                from smartcard.Exceptions import CardConnectionException
                
                #card type
                cardtype = AnyCardType()

                #card request
                cardrequest = CardRequest(timeout=INFINITE, newcardonly=True,cardType=cardtype )
            
                break
            except Exception as ex:
                logging.exception("failed to load smartcard : "+str(ex))
                logging.shutdown()
                time.sleep(2)
                continue
        logging.info("smartcard loaded")
        
        ### DUMP PROCESS ###
        
        while True:
            logging.info("wait card")
            try:
                cardservice = cardrequest.waitforcard()
            except Exception as cte:
                logging.exception("wait card Exception : "+str(cte))
                time.sleep(2)
                continue
            
            logging.info("new card")
            try:
                cardservice.connection.connect()
                
                ## recolt env info ##
                currentDump = dump()
                
                position = gpsProxy.getPosition()
                currentDump.setPosition(*position) 
                currentDump.setAltitude(*gpsProxy.getAltitude())
                
                place = gpsProxy.getPlace()
                if place[4] != None:
                    currentDump.setLocation(*place)
                
                currentDump.setCurrentDatetime()
                currentDump.setExtraInformation("GpsLogId",gpsProxy.getGpsLogId())
                currentDump.setExtraInformation("DumpLogId",self.localid)
                
                ## dump the tag ##
                try:
                    dumpSkipass(cardservice.connection, gpsProxy,MAINREP, self.localid)
                except Exception as e:
                    logging.exception("save dump exception : "+str(e))
                
                #uid is the minimal information needed to save a dump, if it is not available, not saved
                if len(currentDump.getUID()) == 0:
                    logging.warning("empty uid dump, not saved")
                    continue
                
                ## build path name
                dtime = datetime.datetime.now()
                nextDumpID = getLogNextId(path) 
                uid = currentDump.getUIDString().replace(" ","")
                fileName = path+"dump_"+uid+"_"+str(nextDumpID)+"_"+str(dtime).replace(" ","_").replace(":","_").replace(".","_")+".txt"
                logging.info("dump file name : "+fileName)
                if uid in owners:
                    currentDump.getOwner(owners[uid])
                else:
                    currentDump.getOwner("unknown")
                
                ## save the dump ##
                try:
                    saveDump(currentDump, fileName)
                except Exception as e:
                    logging.exception("save dump exception : "+str(e))
                
                ## notify dump event to gps daemon ##
                gpsProxy.addPointOfInterest(position[0], position[1], uid, "dump of "+uid+" at "+dtime.isoformat()+" (file key ="+str(nextDumpID)+")")
                
                ## disconnect dump
                cardservice.connection.disconnect()
            except CardConnectionException as cce:
                logging.exception("CardConnectionException : "+str(cce))
            except Exception as ex:
                logging.exception("dump exception : "+str(ex))
                if self.debug:
                    exit()
                time.sleep(2)
            
        ###
        
if __name__ == "__main__":
    gpsclid = gpsSharing("iso15693dumper")
    gpsclid.main()

    
