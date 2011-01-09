#!/usr/bin/env python

#Import Modules
import os
import sys
import threading
import time
import shutil
from daemon import Daemon
from Pd import Pd
from subprocess import Popen, PIPE

class LoggingObj():

    def __init__(self):
        self.logFile     = os.path.join('/var/log/droneServer.log')
        self.fileHandle  = open(self.logFile, 'w')
        self.logFileLock = threading.Lock()
        self.foreground  = 0

    def writeLine(self, logLine):
        output = self.timeStamp() + '  ' + str(logLine) + '\n'
        if foreground:
            print output
        else:
            self.fileHandle.write(output)
    
    def timeStamp(self):
        stamp = time.strftime("%Y%m%d-%H:%M:%S")
        return stamp
        
        
        
        
class MasterPD(Pd):
        
    def __init__(self, jackManager, comPort=30320, streamPort=30310):
        self.patchName   = 'PD master patch name here'
        Pd.__init__(self, comPort, False, self.patchName)
        self.streamPort  = streamPort
        self.name        = 'masterPD'
        self.activePatch = 2
        self.oldPatch    = 1
        self.fadeTime    = 10
        self.patches     = {}
        self.jackManager = jackManager
        
        self.jackManager.register_program(self)
        
    def streaming_control(self, streamStatus):
        pass
        #self.pdProgram.message('streaming streamStatus')
        
    def channel_fade(self):
        #fade across to new active patch
        message = 'fade %i' % self.activePatch
        self.Send(message)
        
    def pause(self, pauseLength):
        start = time()
        while time() - start < pauseLength:
		    self.Update()
            for number, subPatch in self.patches.items()
                if subPatch.Alive()
                    subPatch.Update()

    def create_new_patch(self):
        
        #change active patch number
        if self.activePatch == 2:
            self.activePatch = 1
            self.oldPatch    = 2
        else:
            self.activePatch = 2
            self.oldPatch    = 1
        #create new patch in the active patch slot
        self.patches[self.activePatch] = PdPatch(self, self.jackManager self.activePatch, self.port)
        
        #register with jack
        self.jackManager.register_program(self.patches[self.activePatch])
        
    def stop_old_patch(self):
        #stop old patch
        if self.patches[self.oldPatch].Alive():
        del(self.patches[self.oldPatch])
    
    def switch_patch(self):
        if self.activePatch == 1:
            self.activePatch = 2
            self.oldPatch    = 1
            
        elif self.activePatch == 2:
            self.activePatch = 1
            self.oldPatch    = 2
            
            
        

class PdPatch(Pd):
        
    def __init__(self, master, jackManager, patchNum, basePort):
        self.patchName   = 'function to randomly choose patch here'
        self.master      = master
        self.patchDir    = 'Patch Directory Here'
        comPort          = basePort + patchNum
        self.name        = 'patch' + patchNum
        self.jackManager = jackManager
        Pd.__init__(self, comPort, False, self.patchName)
        
    def __del__(self):
        self.jackManager.disconnect(self)
        self.Exit
        #might use this to kill jack connections
        
    def register_callbacks(self):
        pass
        #self.pdProgram.message('streaming streamStatus')
        
    def message_pd(self, message):
        pass
        #self.pdProgram.message('message')

    def choose_patch(self):
        pass
        
class ServerDaemon(Daemon):
    
    def run(self):
        
        LogFile = LoggingObj()
        
        LogFile.writeLine('\n\n')
        LogFile.writeLine('Radio Drone Starting Up')
        LogFile.writeLine('')
        
        #create jack connection management object
        jackManager = JackManagement()
        
        #create mixing/streaming patch
        masterPD = MasterPD()
        
        #check that the master PD patch is OK
        if masterPD.Alive:
            pass
            #put something in the logFile
        else:
            #PROBLEM HERE!! LOG IT!!
            exit(1)
        
        
        while True:
            #switch which patch is active
            masterPD.switchPatch()
            
            #tell master PD to create the new patch
            masterPD.create_new_patch()
            
            #kill off old copy of PD which will auto disconnect from jack
            masterPD.stop_old_patch()
                
            #sleep for 10 minutes, untill next patch needs to be loaded
            masterPD.pause(600)
            
            
if __name__ == "__main__":

    daemon = ServerDaemon('/var/run/droneServer.pid')
    
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'foreground' == sys.argv[1]:
            LogFile.foreground = 1
            daemon.run()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart|foreground" % sys.argv[0]
        sys.exit(2)
                
