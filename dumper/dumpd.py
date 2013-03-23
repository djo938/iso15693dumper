#!/usr/bin/python

import logging, os, sys, time
import time
from daemon import Daemon
import Pyro4

#MAINREP = "/home/djo/Bureau/dumpDaemon/dump/"
MAINREP = "/root/dumper/"

#WARNING, the deameon doesn't read the other first sector if these don't exist
firstSectorToRead = [0x1c,0x1d,0x1e]

rangeToRead = []
rangeToRead.extend(firstSectorToRead)
for i in range(0,0x40):
    if not i in firstSectorToRead:
        rangeToRead.append(i)
#TODO BUG doesn't read the first sector if firstSectorToRead don't exist

proxy = None

def getPosition():
    global proxy
    try:
        if proxy == None:
            proxy=Pyro4.Proxy("PYRONAME:dump.gpsdata")

        return proxy.getPosition()

    except Exception as ex:
        proxy = None
        logging.exception("Pyro4 Exception (getPosition) : "+str(ex))
        return "failed to get position"

def getAltitude():
    global proxy
    try:
        if proxy == None:
            proxy=Pyro4.Proxy("PYRONAME:dump.gpsdata")

        return proxy.getAltitude()

    except Exception as ex:
        proxy = None
        logging.exception("Pyro4 Exception (getPosition) : "+str(ex))
        return "failed to get altitude"



def printHexaTable(l, sep=" "):
    if sep == "":
        return ''.join( [ "%02X"%x for x in l ] ).strip()
    else:
        return ''.join( [ "%02X"%x+sep for x in l ] ).strip()[:-1]


def convertNN(NN):
    if (NN == 0x0001): return "NXP Mifare Standard 1k"
    elif (NN == 0x0002): return "NXP Mifare Standard 4k"
    elif (NN == 0x0003): return "NXP Mifare UltraLight"
    elif (NN == 0x0004): return "SLE55R_XXXX"
    elif (NN == 0x0006): return "ST MicroElectronics SR176"
    elif (NN == 0x0007): return "ST MicroElectronics SRIX4K"
    elif (NN == 0x0008): return "AT88RF020"
    elif (NN == 0x0009): return "AT88SC0204CRF"
    elif (NN == 0x000A): return "AT88SC0808CRF"
    elif (NN == 0x000B): return "AT88SC1616CRF"
    elif (NN == 0x000C): return "AT88SC3216CRF"
    elif (NN == 0x000D): return "AT88SC6416CRF"
    elif (NN == 0x000E): return "SRF55V10P"
    elif (NN == 0x000F): return "SRF55V02P"
    elif (NN == 0x0010): return "SRF55V10S"
    elif (NN == 0x0011): return "SRF55V02S"
    elif (NN == 0x0012): return "Texas Instruments TAG IT"
    elif (NN == 0x0013): return "LRI512"
    elif (NN == 0x0014): return "NXP ICODE SLI"
    elif (NN == 0x0015): return "TEMPSENS"
    elif (NN == 0x0016): return "NXP ICODE 1"
    elif (NN == 0x0017): return "PicoPass 2K"
    elif (NN == 0x0018): return "PicoPass 2KS"
    elif (NN == 0x0019): return "PicoPass 16K"
    elif (NN == 0x001A): return "PicoPass 16Ks"
    elif (NN == 0x001B): return "PicoPass 16K(8x2)"
    elif (NN == 0x001C): return "PicoPass 16KS(8x2)"
    elif (NN == 0x001D): return "PicoPass 32KS(16+16)"
    elif (NN == 0x001E): return "PicoPass 32KS(16+8x2)"
    elif (NN == 0x001F): return "PicoPass 32KS(8x2+16)"
    elif (NN == 0x0020): return "PicoPass 32KS(8x2+8x2)"
    elif (NN == 0x0021): return "ST MicroElectronics LRI64"
    elif (NN == 0x0022): return "NXP ICODE UID"
    elif (NN == 0x0023): return "NXP ICODE EPC"
    elif (NN == 0x0024): return "LRI12"
    elif (NN == 0x0025): return "LRI128"
    elif (NN == 0x0026): return "Mifare Mini"
    elif (NN == 0x0027): return "my-d move (SLE 66R01P)"
    elif (NN == 0x0028): return "my-d NFC (SLE 66RxxP)"
    elif (NN == 0x0029): return "my-d proximity 2 (SLE 66RxxS)"
    elif (NN == 0x002A): return "my-d proximity enhanced (SLE 55RxxE)"
    elif (NN == 0x002B): return "my-d light (SRF 55V01P)"
    elif (NN == 0x002C): return "PJM Stack Tag (SRF 66V10ST)"
    elif (NN == 0x002D): return "PJM Item Tag (SRF 66V10IT)"
    elif (NN == 0x002E): return "PJM Light (SRF 66V01ST)"
    elif (NN == 0x002F): return "Jewel Tag"
    elif (NN == 0x0030): return "Topaz NFC Tag"
    elif (NN == 0x0031): return "AT88SC0104CRF"
    elif (NN == 0x0032): return "AT88SC0404CRF"
    elif (NN == 0x0033): return "AT88RF01C"
    elif (NN == 0x0034): return "AT88RF04C"
    elif (NN == 0x0035): return "i-Code SL2"
    elif (NN == 0xFFA0): return "Unidentified 14443 A card"
    elif (NN == 0xFFB0): return "Unidentified 14443 B card"
    elif (NN == 0xFFB1): return "ASK CTS 256B"
    elif (NN == 0xFFB2): return "ASK CTS 512B"
    elif (NN == 0xFFB3): return "ST MicroElectronics SRI 4K"
    elif (NN == 0xFFB4): return "ST MicroElectronics SRI X512"
    elif (NN == 0xFFB5): return "ST MicroElectronics SRI 512"
    elif (NN == 0xFFB6): return "ST MicroElectronics SRT 512"
    elif (NN == 0xFFB7): return "PICOTAG"
    elif (NN == 0xFFC0): return "Calypso card using the Innovatron protocol"
    elif (NN == 0xFFD0): return "Unidentified 15693 card"
    elif (NN == 0xFFD1): return "Unidentified 15693 Legic card"
    elif (NN == 0xFFD2): return "Unidentified 15693 ST MicroElectronics card"
    elif (NN == 0xFFE1): return "NXP ICODE UID-OTP"
    elif (NN == 0xFFE2): return "Unidentified EPC card"
    elif (NN == 0xFFFF): return "Virtual card (test only)"
    else: return "Unknonw Value"

def convertSS(SS):
    if (SS == 0x00): return "No Information given"
    elif (SS == 0x01): return "ISO 14443 A, level 1"
    elif (SS == 0x02): return "ISO 14443 A, level 2"
    elif (SS == 0x03): return "ISO 14443 A, level 3 or 4 (and Mifare)"
    elif (SS == 0x04): return "RFU"
    elif (SS == 0x05): return "ISO 14443 B, level 1"
    elif (SS == 0x06): return "ISO 14443 B, level 2"
    elif (SS == 0x07): return "ISO 14443 B, level 3 or 4"
    elif (SS == 0x08): return "RFU"
    elif (SS == 0x09): return "ISO 15693, level 1"
    elif (SS == 0x0A): return "ISO 15693, level 2"
    elif (SS == 0x0B): return "ISO 15693, level 3"
    elif (SS == 0x0C): return "ISO 15693, level 4"
    elif (SS == 0x0D): return "Contact (7816-10) I2C"
    elif (SS == 0x0E): return "Contact (7816-10) Extended I2C"
    elif (SS == 0x0F): return "Contact (7816-10) 2WBP"
    elif (SS == 0x10): return "Contact (7816-10) 3WBP"
    elif (SS == 0xF0): return "ICODE EPC"
    else: return "Unknonw Value"

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


def dumpSkipass(con):
    #first beep
    con.transmit( [0xff,0xf0,0x0,0x0,0x3,0x1c,0x0,0x82,0x0])

    #read UID
    uid, sw1, sw2 = con.transmit( [0xFF, 0xCA, 0x00, 0x00,0x00] )

    if sw1 != 0x90 and sw2 != 0x00:
        logging.error("failed to get UID with command [0xFF, 0xCA, 0x00, 0x00,0x00], get the following sw : %02X %02X"%(sw1, sw2))
        return

    #build file name
    t = time.localtime()

    f = file(MAINREP+"dump/dump_"+printHexaTable(uid,"")+"_"+str(t.tm_hour)+"h"+str(t.tm_min)+"s"+str(t.tm_sec)+".txt","w")
    logging.info("card uid : "+printHexaTable(uid,":"))
    
    try:
        #append GPS data
        f.write("Position : "+getPosition()+"\nAltitude : "+getAltitude()+"\nHeure : "+str(t.tm_hour)+"h"+str(t.tm_min)+"s"+str(t.tm_sec)+"\n")

        #compute UID and decimal UID
        uid_type = (uid[0] << 16) + (uid[1] << 8) + uid[2]

        uid_dec = 0
        for i in range(0,len(uid)):
            uid_dec += (uid[len(uid)-i-1]<<(i*8))

        f.write("UID : " + printHexaTable(uid)+"\nUID : " + str(uid_dec)+"\n")
        uid.reverse()

        #TODO write process ID

        #read pix
        data, sw1, sw2 = con.transmit( [0xFF, 0xCA, 0xF1, 0x00, 0x00])

        if sw1 != 0x90 and sw2 != 0x00:
            logging.error("failed to get PIX with command [0xFF, 0xCA, 0xF1, 0x00, 0x00], get the following sw : %02X %02X"%(sw1, sw2))
            return

        #compute pix.NN and pix.SS    
        SS = data[0]
        NN = (data[1] << 8) + data[2]

        f.write("PIX.SS : %02X ("%SS + convertSS(SS) + ")\nPIX.NN : %04X ("%NN + convertNN(NN) +")\n")

        #prepare read data instruction
        if uid_type == 0xE01604 or uid_type == 0xE01694:
            # MultiReadBloc
            ins_prefix = [0xFF, 0xFE, 0x04, 0x0B, 0X0C, 0x60, 0x23]
            ins_prefix.extend(uid)
            ins_prefix.extend([0x00, 0x00])
            index_to_index = len(ins_prefix) - 2
            f.write("read type : MULTI READ\n")
        else:
            #single read bloc
            ins_prefix = [0xFF, 0xFE, 0x04, 0x0B, 0X0B, 0x60, 0x20]
            ins_prefix.extend(uid)
            ins_prefix.append(0x00)
            index_to_index = len(ins_prefix) - 1
            f.write("read type : SINGLE READ\n")

        #read all block
        for i in rangeToRead:
            ins_prefix[index_to_index] = i
            data, sw1, sw2 = con.transmit(ins_prefix)

            #end of stream?
            if (sw1 == 0x6F and sw2 == 0x2C) or (sw1 == 0x6F and sw2 == 0x27):
                f.write("end of stream\n")
                break

            sect = "%02x"%i
            #read error?
            if sw1 != 0x90 or sw2 != 0x00:
                logging.error("failed to get read sector "+sect+" with command ["+printHexaTable(ins_prefix)+"], get the following sw : %02X %02X"%(sw1, sw2))
                break

            #empty data?
            if data == None or len(data) == 0:
                f.write("sector "+sect+": null data\n")
                break

            #new data available
            if   data[0] == 0x00:
                f.write("sector "+sect+": "+printHexaTable(data[1:],":")+" (Unlocked)\n")
            elif data[0] == 0x01:
                f.write("sector "+sect+": "+printHexaTable(data[1:],":")+" (Locked)\n")
            else:
                f.write("sector "+sect+": "+printHexaTable(data,":")+"\n")

        #BEEP BEEP BEEEP
        errorBeep(con,0)

    finally: #Whatever append, the file is closed
        f.close()
 
class MyDaemon(Daemon.Daemon):
    def run(self):
        #starting loggin
        #logging.basicConfig(format='%(asctime)s %(message)s')
        logging.basicConfig(format='%(asctime)s %(message)s', filename=MAINREP+'log/skipassDumper'+str(os.getpid())+'.log',level=logging.DEBUG)
        logging.info("server start")
        #put this here, because the context loading must be in in the same process than the run method
        logging.info("smartcard loading")
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
                dumpSkipass(cardservice.connection)
                cardservice.connection.disconnect()
            except CardConnectionException as cce:
                logging.exception("CardConnectionException : "+str(cce))
            except Exception as ex:
                logging.exception("dump exception : "+str(ex))
                time.sleep(2)
 
if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-iso15693dumper.pid')
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
        print "usage: %s start|stop|restart|test" % sys.argv[0]
        sys.exit(2)
    
