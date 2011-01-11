#!/usr/bin/env python

#Import Modules
import os
import sys
from time import time, sleep
import shutil
import random
from Pd import Pd
from daemon import Daemon
from subprocess import Popen, PIPE
from jackManager import JackManagement

logFile = '/var/log/droneServer.log'
pidFile = '/var/run/droneServer.pid'
patchDir = ''

class LoggingObj():

    def __init__(self):
        self.logFile     = os.path.join(logFile)
        self.fileHandle  = open(self.logFile, 'w')
        self.foreground  = 1

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
        
    def __init__(self, comPort=30320, streamPort=30310):
        self.patchName   = 'masterPatch.pd'
        self.streamPort  = streamPort
        self.name        = 'masterPD'
        self.activePatch = 2
        self.oldPatch    = 1
        self.fadeTime    = 10
        self.patches     = {}
        self.playTime    = 600
        self.portList    = {1:[1,2], 2:[3,4]}

        sendCmd = "stream port " + str(self.streamPort)

        extras = "-jack -inchannels 4"
        
        Pd.__init__(self, comPort, False, self.patchName, extra=extras)
        
        
    def streaming_control(self, streamStatus):
        message = "stream " + streamStatus
        self.Send('streaming streamStatus')
        
    def channel_fade(self):
        #fade across to new active patch
        message = 'fade ' + str(self.activePatch) + " " + str(self.fadeTime)
        self.Send(message)
        
    def pause(self, pauseLength):
        start = time()
        while time() - start < pauseLength:
            self.Update()
            for number, subPatch in self.patches.items():
                if subPatch.Alive():
                    subPatch.Update()
    
    def create_new_patch(self):
        #get a random patch from the patch folder
        patchPath = self.get_random_patch()
        #create new patch in the active patch slot
        self.patches[self.activePatch] = PdPatch(self.activePatch, self.port, patchPath)
        #give PD some time to come up ok
        self.pause(5)
        #register the new patch with jack
        newPatch = self.patches[self.activePatch].name
        jackManager.register_program(newPatch)
        #get the ports for the new program
        jackManager.get_ports(newPatch)
        #run disconnect incase its auto connected to the system IOs
        jackManager.disconnect_program(newPatch)
        #now connect the new patch to the master
        jackManager.connect_programs(newPatch, [1,2], self.name,self.portList[self.activePatch])
    
    def get_random_patch(self):
        return 'test1.pd'
        #patchList = os.listdir(patchDir)
        #patch = random.choose(patchList)
        
    def stop_old_patch(self):
        #stop old patch
        return 0
        if self.patches[self.oldPatch] is not None:
            if self.patches[self.oldPatch].Alive():
                jackManager.disconnect_program(self.patches[self.oldPatch].name)
                del(self.patches[self.oldPatch])
    
    def switch_patch(self):
        if self.activePatch == 1:
            self.activePatch = 2
            self.oldPatch    = 1
        elif self.activePatch == 2:
            self.activePatch = 1
            self.oldPatch    = 2
    

class PdPatch(Pd):
        
    def __init__(self, patchNum, basePort, patch):
        self.patchName   = patch
        self.port        = basePort + patchNum
        self.name        = 'patch' + str(patchNum)
        extras = "-jack"
        Pd.__init__(self, self.port, False, self.patchName, extra=extras)

        
class ServerDaemon(Daemon):
    
    def run(self):
        
        #LogFile = LoggingObj()
        
        #LogFile.writeLine('\n\n')
        #LogFile.writeLine('Radio Drone Starting Up')
        #LogFile.writeLine('')
        
        global jackManager

        #create jack connection management object
        jackManager = JackManagement()
        if jackManager.Alive:
            print "Jack is ok"
            pass
            #put something in the logFile
        else:
            #PROBLEM HERE!! LOG IT!!
            exit(1)
        jackManager.register_program("system")
        jackManager.get_ports("system")
        jackManager.disconnect_program("system")

        #create mixing/streaming patch
        masterPD = MasterPD()
        #check that the master PD patch is OK
        if masterPD.Alive:
            pass
            #put something in the logFile
        else:
            #PROBLEM HERE!! LOG IT!!
            exit(1)
        jackManager.register_program(masterPD.name)
        jackManager.get_ports(masterPD.name)
        jackManager.disconnect_program(masterPD.name)

        #start streaming
        masterPD.streaming_control("go")
        
        while True:
            #switch which patch is active
            masterPD.switch_patch()
            
            #tell master PD to create the new patch
            masterPD.create_new_patch()

            #fade over to new patch
            masterPD.channel_fade()
            
            #kill off old copy of PD which will auto disconnect from jack
            masterPD.stop_old_patch()
                
            #sleep for 10 minutes, untill next patch needs to be loaded
            masterPD.pause(masterPD.playTime)
            
            
if __name__ == "__main__":

    daemon = ServerDaemon(pidFile)
    
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'foreground' == sys.argv[1]:
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
                
