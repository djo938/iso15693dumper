#!/usr/bin/python

#built-in import
import logging, os, sys, time, datetime

#local import
from data import owners 

#https://github.com/djo938/ import
from pydaemon import Daemon, getLogNextId 
from dumpformat import dump, dumpManager, byteListToString, saveDump, DATAGROUPFLAG_LOCKED


#the dumper is able to work without gps support
pysharegpsloaded = False
try:
    from pysharegps import sharedGpsClient
    pysharegpsloaded = True
except ImportError:
    pass

MAINREP = "/root/data/dump/"
SHORT_DURATION = 0x64
LONG_DURATION  = 0xff
DUMPTYPE = 0 #(0=any, 1=encapsluated_iso15693, 2=encapsluated_iso15693WithUID)
    #TODO test 1

def getApduAndIndex(uid):
    #TODO check uid_type
    #TODO adapt the code with 4.5.3 page 83 of the proxnroll reference developer guide.
        #also try with the read binary, it will transform this into a universal dumper o.O
        #try in simple process before

    if DUMPTYPE == 1: #iso15693 encapsulated without UID
        if uid_type == 0xE01604 or uid_type == 0xE01694:
            return "ISO15693",[0xff, 0xfe, 0x05, 0x00, 0x04, 0x22, 0x23, 0x00, 0x00], 7 #TODO test it
        else:
            return "ISO15693",[0xff, 0xfe, 0x05, 0x00, 0x03, 0x22, 0x20, 0x00], 7 #TODO test it
        
    else DUMPTYPE == 2: #iso15693 encapsulated with UID
        uid.reverse()
        ins_prefix = []
        index_to_index = 0
        if uid_type == 0xE01604 or uid_type == 0xE01694:
            # MultiReadBloc
                #class : 0xff
                #ins   : 0xfe : encapsulate (proxnroll)
                #arg1  : 0x04 : send frame "as is" using iso15693
                #arg2  : 0x0b : timeout 1 sec
                #data length : 0x0c = 12
                #data  : 0x60 0x23 uid 0x00 0x00
                    #0x60 : ??
                    #0x23 : Read Multiple Blocks 
                    #uid
                    #0x00 : block to read
                    #0x00 : number of block to read XXX 0? not 1?
            ins_prefix = [0xFF, 0xFE, 0x04, 0x0B, len(uid)+4, 0x60, 0x23]
            ins_prefix.extend(uid)
            ins_prefix.extend([0x00, 0x00])
            index_to_index = len(ins_prefix) - 2
        else:
            #single read bloc
                #class : 0xff
                #ins   : 0xfe : encapsulate (proxnroll)
                #arg1  : 0x04 : send frame "as is" using iso15693
                #arg2  : 0x0b : timeout 1 sec
                #data length : 0x0b = 11
                #data  : 0x60 0x20 uid 0x00
                    #0x60 : ??
                    #0x20 : Read Single Block 
                    #uid
                    #0x00 : block to read
            ins_prefix = [0xFF, 0xFE, 0x04, 0x0B, len(uid)+3, 0x60, 0x20]
            ins_prefix.extend(uid)
            ins_prefix.append(0x00)
            index_to_index = len(ins_prefix) - 1
        return "ISO15693",ins_prefix, index_to_index
    else: #any
        return "ANY",[0xff, 0xb0, 0x00, 0x00, 0x00], 3

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


def dumpSkipass(con, currentDump):
    

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
    standart, ins_prefix, index_to_index = getApduAndIndex(uid)
    currentDump.setCommunicationStandard(standart)
    
    #read all block
    for i in range(0,0xffff):
        ins_prefix[index_to_index] = i
        data, sw1, sw2 = con.transmit(ins_prefix)

        #TODO check status word signification
            #http://www.springcard.com/fr/download/find/file/pmd841p 
                #page 13 : 2.1.2 Status words returned by the embedded APDU interpreter
                #page 38 : encapsulate error
                #page 86 : chapter 5, error if sw1 == 0x6f

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

        #add data
        if len(data) > 4:
            currentDataGroup.addDataSector(i, data[1:])
            
            #compute attribute
            if   data[0] == 0x00:
                currentDataGroup.setSectorAttribute(i, DATAGROUPFLAG_LOCKED, False)
            elif data[0] == 0x01:
                currentDataGroup.setSectorAttribute(i, DATAGROUPFLAG_LOCKED, True)
        else:
            currentDataGroup.addDataSector(i, data)
        
    #BEEP BEEP BEEEP
    errorBeep(con,0)
 
class MyDaemon(Daemon):
    def run(self):
        ### INIT GPS SUPPORT ### 
        if pysharegpsloaded:
            logging.info("gps support enabling...")
            gpsProxy = sharedGpsClient()
            if gpsProxy.isInit():
                logging.info("gps support enabled")
            else:
                logging.info("gps support not enabled. retry later.")
        else:
            logging.warning("gps support not installed")
            gpsProxy = None
        
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
            currentDump = None
            fileName = None
            try:
                #init dump recording
                currentDump = dump() #and new dump object
                
                ## dump the tag ##
                try:
                    cardservice.connection.connect()#connect to the card
                    dumpSkipass(cardservice.connection, currentDump)             
                    cardservice.connection.disconnect()## disconnect dump
                except CardConnectionException as cce:
                    logging.exception("CardConnectionException : "+str(cce))
                except Exception as e:
                    logging.exception("save dump exception : "+str(e))
                
                ## recolt and process env info ##
                
                #build a first simple file name
                dtime = datetime.datetime.now()
                fileName = str(dtime).replace(" ","_").replace(":","_").replace(".","_")+".txt"

                currentDump.setCurrentDatetime()
                currentDump.setExtraInformation("DumpProcessLogId",self.localid)
                nextDumpID = getLogNextId(MAINREP)
                fileName = str(nextDumpID)+"_"+fileName
                currentDump.setExtraInformation("DumpFileId",nextDumpID)
                logging.info("DumpFileId : "+str(nextDumpID))
                
                ## UID management ##
                    #uid is the minimal information needed to save a dump, if it is not available, not saved
                        #a tag has always an uid, if it is not set, the connection had been broke before to read it
                
                uid = None
                if len(currentDump.getUID()) == 0:
                    logging.warning("empty uid")
                else:
                    # update path name
                    uid = currentDump.getUIDString().replace(" ","")
                    fileName = uid+"_"+fileName
                    
                    if uid in owners:
                        currentDump.setOwner(owners[uid])
                    else:
                        currentDump.setOwner("unknown")
                        logging.warning("uid not in the owner list")
                    
                    logging.info("dump uid: "+uid)
                    
                ## gps management ##
                if gpsProxy != None: #is there gps support ?
                    if gpsProxy.isInit():
                        position = gpsProxy.getSharedObject().getPosition()
                        print position
                        currentDump.setPosition(*position) 
                        print gpsProxy.getSharedObject().getAltitude()
                        currentDump.setAltitude(*gpsProxy.getSharedObject().getAltitude())
                        
                        place = gpsProxy.getSharedObject().getPlace()
                        if place[4] != None:
                            currentDump.setLocation(*place)
                        
                        currentDump.setExtraInformation("GpsLogId",gpsProxy.getSharedObject().getGpsLogId())
                        
                        if uid != None:
                            gpsProxy.getSharedObject().addPointOfInterest(position[0], position[1], uid, "dump of "+uid+" at "+dtime.isoformat()+" (file key ="+str(nextDumpID)+")")
                    else:
                        currentDump.setExtraInformation("gps","gps support does not work")
                        logging.warning("need to re init pyro")
                        gpsProxy.reInit()
                else:
                    currentDump.setExtraInformation("gps","gps support is not supported")
            except Exception as ex:
                logging.exception("dump exception : "+str(ex))
                
                if self.debug:
                    exit()
                time.sleep(2) 
                #wait two secs to allow the system to stabilyse if the environment is not ready
                #and also to prevent a log rush if the problem is still present at the next iteration
            finally: ## save the dump ##
                if currentDump == None or fileName == None:
                    logging.critical("Can't save the dump, currentDump or fileName is None")
                else:
                    try:
                        saveDump(currentDump, MAINREP+"dump_"+fileName)
                    except Exception as e:
                        logging.exception("save dump exception : "+str(e))
            
        ###
        
if __name__ == "__main__":
    daem = MyDaemon("iso15693dumper")
    daem.main()

    
