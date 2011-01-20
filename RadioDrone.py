#!/usr/bin/env python

#Import Modules
import os
import re
import sys
import shutil
import random
from Pd import Pd
from time import time, strftime
from daemon import Daemon

logFile   = '/var/log/droneServer.log'
pidFile   = '/var/run/droneServer.pid'
cfgFile   = 'config.cfg'
patchDir  = './patches'
masterDir = './master'

class LoggingObj():

    def __init__(self, foreground=False):
        self.logFile    = os.path.join('')
        self.foreground = foreground
        if not foreground:
            self.fileHandle = open(self.logFile, 'w')

    def log(self, logLine):
        output = "%s  %s" % (self.timeStamp(), logLine)
        if self.foreground:
            print output
        else:
            self.fileHandle.write(output)
    
    def timeStamp(self):
        stamp = strftime("%Y%m%d-%H:%M:%S")
        return stamp
    
class Config():
    #Class for loading and holding the config data
    
    def __init__(self, cfgFile):
        cfgData = open(cfgFile)
        
        for line in cfgData:
            line = line.rstrip()
            param,val = line.split(':')
            if param == 'host':
                self.host = val
            elif param == 'streamport':
                self.strmPort = val
            elif param == 'comPort':
                self.comPort = val
            elif param == 'mountPoint':
                self.mount = val
            elif param == 'password':
                self.password = val
            elif param == 'samplerate':
                self.sRate = val
            elif param == 'channels':
                self.chans = val
            elif param == 'maxBitrate':
                self.maxBr = val
            elif param == 'nomBitrate':
                self.nomBr = val
            elif param == 'minBitrate':
                self.minBr = val
            elif param == 'fadeTime':
                self.fade = val
            elif param == 'playTime':
                self.play = val
            else:
                logFile.log("CFG ERROR: %s is not a known parameter" % param)
            
        cfgData.close()
    
class SubPatch():
    #Class for holding information about sub patches
    
    def __init__(self, number):
        self.name   = "patch%i" % number
        self.patch  = ""
        self.pdNum  = 0
        self.ok     = False
    

class PureData(Pd):
        
    def __init__(self, gui=False):
        self.patchName   = 'masterPatch.pd'
        
        self.config      = Config(cfgFile)
        
        self.active      = 2
        self.old         = 1
        
        self.patches     = {}
        self.patches[1]  = SubPatch(1)
        self.patches[2]  = SubPatch(2)
        
        self.fadeTime    = int(self.config.fade)
        self.playTime    = int(self.config.play)
        
        comPort          = int(self.config.comPort)
        
        self.gui         = gui
        
        self.regWait     = False
        self.regTimeout  = 20
        self.loadError   = False
        self.connection  = False
        
        self.fileMatch   = re.compile("^main-.*?\.pd$")
        
        extras           = "-alsa"
        
        path             = [patchDir, masterDir]
        
        Pd.__init__(self, comPort, self.gui, self.patchName, extra=extras, path=path)
        
        logFile.log(self.argLine)
    
    def check_alive(self):
        if self.Alive:
            logFile.log('PureData has started fine')
        else:
            logFile.log('Problem starting PureData')
            sys.exit(2)
    
    def check_network(self):
        logFile.log('Waiting for PD to register the connection')
        wait = 0
        while not self.connection:
            self.pause(1)
            wait += 1
            if wait > 20:
                logFile.log('Problem connecting to PD')
                sys.exit(2)
    
    def Pd_connection(self, data):
        type = data[0]
        val  = data[1]
        if type == "status":
            if val == "1":
                logFile.log('Network connection to PD is up')
                self.connection = True
    
    def pause(self, pauseLength):
        #pause for a specified number of seconds
        #will keep updating the master patch and sub patches
        #so that network communication still works
        logFile.log("Pausing for %i seconds" % pauseLength)
        start = time()
        while time() - start < pauseLength:
            self.Update()
    
    def streaming_setup(self):
        #send a message to the streaming controls in the master patch
        
        config     = self.config
        
        password   = config.password
        hostInfo   = [config.host, config.mount, config.strmPort]
        settings   = [config.sRate, config.chans, config.maxBr, config.nomBr, config.minBr]
        
        message = ["stream", "password", password]
        self.Send(message)
        
        logFile.log("HostInfo is %s" % str(hostInfo))
        message = ["stream", "hostinfo", " ".join(hostInfo)]
        self.Send(message)
        
        logFile.log("Stream Info is %s" % str(settings))
        message = ["stream", "settings", " ".join(settings)]
        self.Send(message)
        
        logFile.log("Connecting")
        message = ["stream", "connect", 1]
        self.Send(message)
        
    
    def switch_patch(self):
        #change the active patch number
        #real scrappy, needs to be neater
        if self.active == 1:
            self.active = 2
            self.old    = 1
        elif self.active == 2:
            self.active = 1
            self.old    = 2
        name = "patch%i" % self.active
        logFile.log("Changing active patch to be %s" % name)
    
    def create_new_patch(self):
        
        self.loadError = False
        
        #get a random patch from the patch folder
        patch, path = self.get_random_patch()
        name = self.patches[self.active].name
        logFile.log("Loading new patch for %s" % name)
        
        #update patch object in active slot
        self.patches[self.active].patch = patch
        self.patches[self.active].path  = path
        
        logFile.log("New Patch - %s in %s" % (patch, path))
        self.Send(['open', 'path', path])
        self.Send(['open', 'patch', patch])
        
        #change regWait to true. We will wait untill the patch is registered
        self.regWait = True
        
        #pause until the patch registers
        #if it doesn't register in a certain time
        #then we have a problem
        errCount = 0
        while self.regWait:
            self.pause(1)
            errCount += 1
            if errCount > self.regTimeout:
                self.loadError = True
                break
    
    def get_random_patch(self):
        #get a random patch from the patch directory
        #currently just returns the test patch
        #will need to figure out how this is going to work

        current = self.patches[self.old].patch
        logFile.log("Active patch is %s" % current)
        
        found = False
        while not found:
            dirList = os.listdir(patchDir)
            dataDir = os.path.join(patchDir, random.choice(dirList))
            
            fileList = os.listdir(dataDir)
            for file in fileList:
                if self.fileMatch.search(file):
                    break
        
            logFile.log("Chosen %s as new patch" % file)
            logFile.log("Check if %s is %s" % (file, current))
            if file != current:
                logFile.log("Is not the same as the old patch")
                found = True
            else:
                logFile.log("%s is the same patch as the current one" % file)
                logFile.log("Will search again")
        
        patchInfo = (file, dataDir)
        return patchInfo
    
    def load_error(self):
        #notifies when there has been an error loading a patch
        patch = self.patches[self.active].patch
        path  = self.patches[self.active].path
        
        logFile.log("***************************************")
        logFile.log("Problem loading %s from %s" % (patch, path))
        logFile.log("Unloading patch and starting again")
        
        message = ['close', patch]
        self.Send(message)
    
    def activate_patch(self):
        #turn on DSP in new patch
        name = self.patches[self.active].name
        logFile.log("Turning on DSP in %s" % name)
        message = [name, 'dsp', 1]
        self.Send(message)
        self.pause(1)
    
    def crossfade(self):
        #fade across to new active patch
        newName = self.patches[self.active].name
        logFile.log("Fading over to %s" % newName)
        
        message = ['volume', 'fade', self.fadeTime]
        self.Send(message)
        
        message = ['volume', 'chan', self.active]
        self.Send(message)
        
        #pause while the fade occours
        self.pause(self.fadeTime)
    
    def kill_old_patch(self):
        #disconnect old patch from master patch and then del the object
        name  = self.patches[self.old].name
        if self.patches[self.old].ok:
            patch = self.patches[self.old].patch
            logFile.log("Stopping %s" % name)
            
            message = [name, 'dsp', 0]
            self.Send(message)
            
            reg = 'reg%i' % self.old
            self.Send([reg, 0])
            
            self.pause(1)
            
            message = ['close', patch]
            self.Send(message)
            self.patches[self.old].ok = False
        else:
            logFile.log("%s doesn't seem to be running currently" % name)
    
    def Pd_register(self, data):
        #Gets the unique number from the PD subPatch
        #This is sent to the Master Patch to change send and receieve
        #   objects so that the two can communicate
        pdNum = data[0]
        self.patches[self.active].pdNum = pdNum
        self.patches[self.active].ok    = True
        name  = self.patches[self.active].name
        logFile.log("Registering number %s to %s" % (pdNum, name))
        
        reg = 'reg%i' % self.active
        message = [reg, pdNum]
        self.Send(message)
        
        #set regWait to False. Patch is registered
        self.regWait = False
    
    def PdMessage(self, data):
        logFile.log("Message from PD:%s" % str(data))
    
    def Error(self, error):
        if error[0] == "print:":
            logFile.log("PD print:%s" % str(error[1:]))
        elif error[0] == "oggcast~:":
            logFile.log("OggCast:%s" % str(error[1:]))
        else:
            logFile.log("stderr from PD:%s" % str(error))
    
    def PdStarted(self):
        logFile.log("PD has started")
    
    def PdDied(self):
        logFile.log("PD has died")
    
    def ComError(self, data):
        logFile.log("Communication error :%s" % str(error))
    

def main():
    
    global logFile

    logFile = LoggingObj()
    
    logFile.log('\n\n')
    logFile.log('Radio Drone Starting Up')
    logFile.log('')
    
    #TODO: pass a reference to the logFile to the puredata Object

    #create mixing/streaming patch
    puredata = PureData()
    puredata.pause(1)
    
    #check that pure data is running fine
    puredata.check_alive()
    
    #check that Python and PD are connected
    puredata.check_network()
    
    #Turn on DSP for pure data
    puredata.Send(['dsp', 1])
    
    #start streaming
    puredata.streaming_setup()
    
    while True:
        #switch which patch is active assuming not in error state
        if not puredata.loadError:
            puredata.switch_patch()
        
        #tell master PD to create the new patch
        puredata.create_new_patch()
        
        if puredata.loadError:
            #call function to deal with loading error
            puredata.load_error()
        else:
            #turn the DSP in the new patch on
            puredata.activate_patch()
            
            #fade over to new patch
            puredata.crossfade()
            
            #kill off old patch
            puredata.kill_old_patch()
            
            #pause untill next patch needs to be loaded
            puredata.pause(puredata.playTime)
        

if __name__ == "__main__":
    main()

