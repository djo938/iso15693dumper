#!/usr/bin/python

from daemon import Daemon
import logging,os,time
import gobject
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from optparse import OptionParser

#MAINREP = "/home/djo/Bureau/dumpDaemon/dump/"
MAINREP = "/root/pairing/"
#TODO check the different capability mode
capability = "KeyboardDisplay" #autre possibilite : "KeyboardDisplay", "DisplayOnly", "DisplayYesNo", "KeyboardOnly" and "NoInputNoOutput"
ADAPTATER = "hci0"
passkey = "1234"
PIN = "1234"
DISTANT_DEVICE = "D8:B3:77:27:D7:45"
DISTANT_DEVICE_ = DISTANT_DEVICE.replace(":","_")

def checkDevice(device):
    if not device.endswith(DISTANT_DEVICE_)
        logging.warning("An unknown remote device try to pair, "+device)
        raise Rejected("Connection rejected by pairingd, not allowed remote host")
    
class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"

class Agent(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method("org.bluez.Agent",in_signature="", out_signature="")
    def Release(self):
        logging.info("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method("org.bluez.Agent",in_signature="os", out_signature="")
    def Authorize(self, device, uuid):
        logging.info("Authorize (%s, %s)" % (device, uuid))
        checkDevice(device)
        #TODO uuid?

    @dbus.service.method("org.bluez.Agent",in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        logging.info("RequestPinCode (%s)" % (device))
        checkDevice(device)
        return PIN

    @dbus.service.method("org.bluez.Agent",in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        logging.info("RequestPasskey (%s)" % (device))
        checkDevice(device)
        return dbus.UInt32(passkey)

    @dbus.service.method("org.bluez.Agent",in_signature="ou", out_signature="")
    def DisplayPasskey(self, device, passkey):
        logging.info("DisplayPasskey (%s, %06d)" % (device, passkey))

    @dbus.service.method("org.bluez.Agent",in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        logging.info("RequestConfirmation (%s, %06d)" % (device, passkey))
        checkDevice(device)
        #TODO passkey?

    @dbus.service.method("org.bluez.Agent",in_signature="s", out_signature="")
    def ConfirmModeChange(self, mode):
        logging.info("ConfirmModeChange (%s)" % (mode))

    @dbus.service.method("org.bluez.Agent", in_signature="", out_signature="")
    def Cancel(self):
        logging.info("Cancel")

class MyDaemon(Daemon.Daemon):

    def run(self):
        logging.basicConfig(format='%(asctime)s %(message)s', filename=MAINREP+'log/bluetoothPairing'+str(os.getpid())+'.log',level=logging.DEBUG)
      
        while True:
            try:
                dbus.mainloop.glib.DBusGMainLoop(set_as_default=True) #use the mainloop of python, to catch the event
                #connect to system bus
                bus = dbus.SystemBus() # (system bus is available for each session, it's not the session bus)
                
                #connect to the interface
                manager = dbus.Interface(bus.get_object("org.bluez", "/"),"org.bluez.Manager") #connect to the object org.bluez.Manager of the application org.bluez
                path = manager.FindAdapter(ADAPTATER) #l'adaptateur existe?
                
                logging.info("device : "+str(path))
            
                #connect to the local adaptater
                adapter = dbus.Interface(bus.get_object("org.bluez", path),"org.bluez.Adapter") #connect to the object org.bluez.Adapter of the application org.bluez.PATH
            except Exception as ex:
                logging.exception("dbus exception : "+str(ex))
                time.sleep(2)
                continue

            try: 
                #TODO test it
                device = adapter.FindDevice(DISTANT_DEVICE)

		#TODO if device found, don't register with it, stop the service

                adapter.RemoveDevice(device)            
            except Exception as ex:
                logging.exception("remove device exception : "+str(ex))

            try:
                path = "/test/agent"
                agent = Agent(bus, path) #on cree l'agent qui va etre utilise sur le bus
                
                mainloop = gobject.MainLoop() #on prepare la boucle principale pour la reception des events
                
                #register the agent
                adapter.RegisterAgent(path, capability)
                
                logging.info("wait pairing")
                mainloop.run()
            except Exception as ex:
                logging.exception("pairing exception : "+str(ex))
                time.sleep(2)
    
if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-bluetoothpairing.pid')
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
