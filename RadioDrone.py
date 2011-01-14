
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
        
        
        
class PureData(Pd):
        
    def __init__(self, comPort=30320, streamPort=30310, debug=False):
        self.patchName   = 'masterPatch.pd'
        self.streamPort  = streamPort
        
        self.activePatch = 2
        self.oldPatch    = 1
        
        self.patches     = {}
        self.patchNames  = {}
        
        self.playTime    = 30
        self.debug       = debug

        gui              = self.debug
        extras           = "-alsa"
        
        Pd.__init__(self, comPort, gui, self.patchName, extra=extras)
        
        logFile.log(self.args)
    
    def pause(self, pauseLength):
        #pause for a specified number of seconds
        #will keep updating the master patch and sub patches
        #so that network communication still works
        logFile.log("Pausing for %i seconds" % pauseLength)
        start = time()
        while time() - start < pauseLength:
            self.Update()
    
    def streaming_control(self, streamControl):
        #send a message to the streaming controls in the master patch
        logFile.log("Streaming control, %s" % streamControl)
        message = ["stream", "control", streamControl]
        self.Send(message)
    
    def switch_patch(self):
        #change the active patch number
        #real scrappy, needs to be neater
        if self.activePatch == 1:
            self.activePatch = 2
            self.oldPatch    = 1
        elif self.activePatch == 2:
            self.activePatch = 1
            self.oldPatch    = 2
    
    def create_new_patch(self):
        #get a random patch from the patch folder
        patchName, patchPath = self.get_random_patch()
        self.patchNames[self.activePatch] = patchName
        #create new patch in the active patch slot
        logFile.log("Opening new patch: %s in %s" % (patchName, patchPath)
        self.Send(['open', 'path', patchPath])
        self.Send(['open', 'patch', patchName])
        self.pause(1)
    
    def get_random_patch(self):
        #get a random patch from the patch directory
        #currently just returns the test patch
        #will need to figure out how this is going to work
        fileName = 'test%i.pd' % self.activePatch
        patchInfo = (fileName, '/home/guy/gitrepositories/Radio-PD/patches')
        return patchInfo
        #patchList = os.listdir(patchDir)
        #patch = random.choose(patchList)
    
    def activate_patch(self):
        patch = 'patch' + str(self.activePatch)
        logFile.log("Turning on DSP in %s" % patch)
        message = [patch, 'dsp', 1]
        self.Send(message)
    
    def crossfade(self):
        #fade across to new active patch
        newPatch = 'patch%i' % self.activePatch
        oldPatch = 'patch%i' % self.oldPatch
        logFile.log("Fading over to %s" % patch)
        
        newmessage = [newPatch, 'volume', 1]
        oldmessage = [oldPatch, 'volume', 0]
        
        self.Send(newmessage)
        self.Send(oldmessage)
        
        self.pause(10)
    
    def kill_old_patch(self):
        #disconnect old patch from master patch and then del the object
        if self.oldPatch in self.patches.keys():
            patch = self.patchNames[self.oldPatch]
            logFile.log("Stopping %s" % patch)
            message = [patch, 'dsp', 0]
            self.Send(message)
            self.pause(1)
            message = ['close', patchName]
            self.Send(message)
            del(self.patches[self.oldPatch])
        pass
    
    def Pd_register(self, data):
        patchNum = data[0]
        patchName = 'patch%i' % self.activePatch
        logFile.log(" Registering number %i to %s" % (patchNum, patchName))
        self.patches[self.activePatch] = patchNum
        reg = 'reg%i' % self.activePatch
        message = [reg, patchNum]
        self.Send(message)
    
    def PdMessage(self, data):
        logFile.log("Message from PD:" + str(data))
    
    def Error(self, error):
        logFile.log("stderr from PD:" + str(error))
    
    def PdStarted(self):
        logFile.log("PD has started")
    
    def PdDied(self):
        logFile.log("PD has died")
    

class ServerDaemon(Daemon):
    
    def run(self, foreground=False):
        
        logFile = LoggingObj(foreground)
        
        logFile.log('\n\n')
        logFile.log('Radio Drone Starting Up')
        logFile.log('')
        
        global logFile

        #create mixing/streaming patch
        puredata = PureData(debug=foreground)
        puredata.pause(1)
        #check that the master PD patch is OK
        if puredata.Alive:
            logFile.log('PureData has started fine')
        else:
            logFile.log('Problem starting PureData')
            exit(1)

        puredata.Send(['dsp', 1])
        
        #start streaming
        #puredata.streaming_control("go")
        
        while True:
            #switch which patch is active
            puredata.switch_patch()
            
            #tell master PD to create the new patch
            puredata.create_new_patch()
            
            puredata.pause(5)
            
            puredata.activate_patch()
            
            #fade over to new patch
            puredata.crossfade()
            
            #kill off old patch
            puredata.kill_old_patch()
            
            #sleep for 10 minutes, untill next patch needs to be loaded
            puredata.pause(puredata.playTime)
            

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
        
