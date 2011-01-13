#!/usr/bin/env python

#Import Modules
import os
import sys
import shutil
import random
from Pd import Pd
from time import time, sleep, strftime
from daemon import Daemon
from subprocess import Popen, PIPE
from jackManager import JackManagement

logFile = '/var/log/droneServer.log'
pidFile = '/var/run/droneServer.pid'
patchDir = ''

class LoggingObj():

    def __init__(self, foreground):
        self.logFile    = os.path.join('')
        self.foreground = foreground
        if not foreground:
            self.fileHandle = open(self.logFile, 'w')

    def log(self, logLine):
        output = self.timeStamp() + '  ' + str(logLine) + '\n'
        if self.foreground:
            print output
        else:
            self.fileHandle.log(output)
    
    def timeStamp(self):
        stamp = strftime("%Y%m%d-%H:%M:%S")
        return stamp
        
        
        
class MasterPD(Pd):
        
    def __init__(self, comPort=30320, streamPort=30310, foreground=False):
        self.patchName   = 'masterPatch.pd'
        self.streamPort  = streamPort
        self.name        = 'masterPD'
        self.activePatch = 2
        self.oldPatch    = 1
        self.fadeTime    = 10
        self.patches     = {}
        self.playTime    = 30
        self.portList    = {1:[1,2], 2:[3,4]}
        self.foreground  = foreground

        gui              = self.foreground
        extras           = "-jack -inchannels 4 -audiobuf 4096"
        
        Pd.__init__(self, comPort, gui, self.patchName, extra=extras)
        
        
    def streaming_control(self, streamStatus):
        #send a message to the streaming controls in the master patch
        message = [stream, control, streamStatus]
        self.Send(message)
        
    def channel_fade(self):
        #fade across to new active patch
        message = ['fade', self.activePatch, self.fadeTime]
        print message
        self.Send(message)
        pauseTime = self.fadeTime + 5
        self.pause(pauseTime)
        
    def pause(self, pauseLength):
        #pause for a specified number of seconds
        #will keep updating the master patch and sub patches
        #so that network communication still works
        print "pausing for a bit"
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
        self.patches[self.activePatch] = PdPatch(self.activePatch, self.port, self.foreground, patchPath)
        #give PD some time to come up ok
        self.pause(1)
        
        #register the new patch with jack
        newPatch = self.patches[self.activePatch].name
        jackManager.register_program(newPatch)
        #get the ports for the new program
        jackManager.get_ports(newPatch)
        #run disconnect incase its auto connected to the system IOs
        jackManager.disconnect_program(newPatch)
        #now connect the new patch to the master
        jackManager.connect_programs(newPatch, [1,2], self.name,self.portList[self.activePatch])
        self.pause(1)
        self.patches[self.activePatch].Send(['dsp', 1])
        
    def get_random_patch(self):
        #get a random patch from the patch directory
        #currently just returns the test patch
        #will need to figure out how this is going to work
        return 'test1.pd'
        #patchList = os.listdir(patchDir)
        #patch = random.choose(patchList)
        
    def stop_old_patch(self):
        #disconnect old patch from master patch and then del the object
        print "************************************ old patch value " + str(self.oldPatch)
        if self.oldPatch in self.patches.keys():
            if self.patches[self.oldPatch].Alive():
                self.patches[self.oldPatch].Send(['dsp', 0])
                self.pause(1)
                jackManager.disconnect_program(self.patches[self.oldPatch].name)
                self.pause(1)
                self.patches[self.oldPatch].Exit()
                del(self.patches[self.oldPatch])
    
    def switch_patch(self):
        #change the active patch number
        #real scrappy, needs to be neater
        if self.activePatch == 1:
            self.activePatch = 2
            self.oldPatch    = 1
        elif self.activePatch == 2:
            self.activePatch = 1
            self.oldPatch    = 2
   
    #def PdMessage(self, data):
    #    logFile.log(self.name + " Message from PD:" + data)
   # 
   # def Error(self, error):
   #     logFile.log(self.name + " stderr from PD:" + error)
   # 
   # def PdStarted(self):
   #     logFile.log(self.name + " has started")
   # 
   # def PdDied(self):
   #     logFile.log(self.name + " has died")

class PdPatch(Pd):
        
    def __init__(self, patchNum, basePort, foreground, patch):
        
        self.patchName  = patch
        port            = basePort + patchNum
        self.name       = 'patch' + str(patchNum)
        
        gui = foreground
        extras = "-jack -audiobuf 4096"
        
        Pd.__init__(self, port, gui, self.patchName, extra=extras)
    

class ServerDaemon(Daemon):
    
    def run(self, foreground=False):
        
        logFile = LoggingObj(foreground)
        
        logFile.log('\n\n')
        logFile.log('Radio Drone Starting Up')
        logFile.log('')
        
        global jackManager
        global logFile

        #create jack connection management object
        jackManager = JackManagement(debug=foreground)
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
        masterPD = MasterPD(foreground=foreground)
        masterPD.pause(5)
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

        jackManager.connect_programs(masterPD.name,[1,2],"system",[1,2])

        masterPD.Send(['dsp', 1])

        #start streaming
        #masterPD.streaming_control("go")
        
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
            daemon.run(True)
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
                
