#!/usr/bin/env python

#Import Modules
import os
import re
import sys
import random
from Pd import Pd
from time import time, strftime


class LoggingObj():

    def __init__(self):
        self.header()

    def write(self, logLine):
        print "%s   %s\n" % (self.timeStamp(), logLine)
    
    def timeStamp(self):
        return strftime("%Y%m%d-%H:%M:%S")
    
    def header(self):
        print "\n*******************\nStartingUp\n*******************\n"
    
class Config():
    #Class for loading and holding the config data
    
    def __init__(self, cfgFile):
        cfgData = open(cfgFile)
        
        #TODO: this is scrappy as hell. improve it
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
            elif param == 'patchDir':
                self.patchDir = val
            elif param == 'masterDir':
                self.masterDir = val
            else:
                self.log.write("CfgError:%s isn't a known parameter" % param)
            
        cfgData.close()
    
class SubPatch():
    #Class for holding information about sub patches
    
    def __init__(self, number):
        self.name   = "patch%i" % number
        self.patch  = ""
        self.pdNum  = 0
        self.ok     = False
    

class PureData(Pd):
        
    def __init__(self, configFile):
        
        self.patch   = 'masterPatch.pd'
        
        self.log         = LoggingObj()
        
        #TODO: have the config file path passed
        #      as an argument to the script
        self.config      = Config(configFile)
        
        self.active      = 2
        self.old         = 1
        
        self.patches     = {1:SubPatch(1), 2:SubPatch(2)}
        
        self.fadeTime    = int(self.config.fade)
        self.playTime    = int(self.config.play)
        
        comPort          = int(self.config.comPort)
        
        gui              = False
        
        self.regWait     = False
        self.regTimeout  = 20
        self.loadError   = False
        self.connection  = False
        
        self.fileMatch   = re.compile("^main-.*?\.pd$")
        
        extras           = "-alsa"
        
        path             = [self.config.patchDir, self.config.masterDir]
        
        Pd.__init__(self, comPort, gui, self.patch, extra=extras, path=path)
        
        self.log.write("Starting PD Process:%s" % self.argLine)
    
    def check_alive(self):
        if self.Alive:
            self.log.write('PD started fine')
        else:
            self.log.write('Problem starting PD')
            sys.exit(2)
    
    def check_network(self):
        self.log.write('Waiting for PD to register the connection')
        wait = 0
        while not self.connection:
            self.pause(1)
            wait += 1
            if wait > 20:
                self.log.write('Problem connecting to PD')
                sys.exit(2)
    
    def Pd_connection(self, data):
        type = data[0]
        val  = data[1]
        if type == "status":
            if val == "1":
                self.log.write('Network connection to PD is up')
                self.connection = True
    
    def pause(self, pauseLength):
        #pause for a specified number of seconds
        #will keep updating the master patch and sub patches
        #so that network communication still works
        start = time()
        while time() - start < pauseLength:
            self.Update()
    
    def streaming_setup(self):
        #send a message to the streaming controls in the master patch
        self.log.write("Setting up streaming")
        config     = self.config
        
        password   = config.password
        
        hostInfo   = [config.host]
        hostInfo.append(config.mount)
        hostInfo.append(config.strmPort)
        
        settings   = [config.sRate]
        settings.append(config.chans)
        settings.append(config.maxBr)
        settings.append(config.nomBr)
        settings.append(config.minBr)
        
        self.Send(["stream", "password", password])
        
        self.log.write("HostInfo is %s" % str(hostInfo))
        self.Send(["stream", "hostinfo", " ".join(hostInfo)])
        
        self.log.write("Stream Info is %s" % str(settings))
        self.Send(["stream", "settings", " ".join(settings)])
        
        self.log.write("Attempting connection to Icecast")
        self.Send(["stream", "connect", 1])
        
    
    def switch_patch(self):
        #change the active patch number
        #TODO: real scrappy, needs to be neater
        if self.active == 1:
            self.active = 2
            self.old    = 1
        elif self.active == 2:
            self.active = 1
            self.old    = 2
        name = "patch%i" % self.active
        self.log.write("Changing active patch to be %s" % name)
    
    def create_new_patch(self):
        
        self.loadError = False
        
        #get a random patch from the patch folder
        patch, path = self.get_random_patch()
        name = self.patches[self.active].name
        self.log.write("Loading new patch for %s" % name)
        
        #update patch object in active slot
        self.patches[self.active].patch = patch
        self.patches[self.active].path  = path
        
        self.log.write("New Patch is %s in %s" % (patch, path))
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
        patchDir = self.config.patchDir
        
        found = False
        while not found:
            dirList = os.listdir(patchDir)
            dataDir = os.path.join(patchDir, random.choice(dirList))
            
            fileList = os.listdir(dataDir)
            
            main = False
            for file in fileList:
                if self.fileMatch.search(file):
                    main = True
                    break
        
            if main:
                self.log.write("Chosen %s as new patch" % file)
                if file != current:
                    self.log.write("Is not the same as the old patch")
                    found = True
                else:
                    self.log.write("%s is also the current patch" % file)
                    self.log.write("Choosing again.")
            else:
                self.log.write("Error:folder %s has no main patch" % dataDir)
                self.log.write("Choosing again.")
        
        patchInfo = (file, dataDir)
        return patchInfo
    
    def load_error(self):
        #notifies when there has been an error loading a patch
        patch = self.patches[self.active].patch
        path  = self.patches[self.active].path
        
        self.log.write("Error:***************************************")
        self.log.write("Error:Problem loading %s from %s" % (patch, path))
        self.log.write("Error:Unloading patch and starting again")
        
        self.Send(['close', patch])
    
    def activate_patch(self):
        #turn on DSP in new patch
        name = self.patches[self.active].name
        self.log.write("Turning on DSP in %s" % name)
        self.Send([name, 'dsp', 1])
        self.pause(1)
    
    def crossfade(self):
        #fade across to new active patch
        newName = self.patches[self.active].name
        self.log.write("Fading over to %s" % newName)
        
        self.Send(['volume', 'fade', self.fadeTime])
        
        self.Send(['volume', 'chan', self.active])
        
        #pause while the fade occours
        self.pause(self.fadeTime)
    
    def kill_old_patch(self):
        #disconnect old patch from master patch and then del the object
        name  = self.patches[self.old].name
        if self.patches[self.old].ok:
            patch = self.patches[self.old].patch
            self.log.write("Stopping %s" % name)
            
            self.Send([name, 'dsp', 0])
            
            reg = 'reg%i' % self.old
            self.Send([reg, 0])
            
            self.pause(1)
            
            self.Send(['close', patch])
            self.patches[self.old].ok = False
        else:
            self.log.write("%s doesn't seem to be running" % name)
    
    def Pd_register(self, data):
        #Gets the unique number from the PD subPatch
        #This is sent to the Master Patch to change send and receieve
        #   objects so that the two can communicate
        pdNum = data[0]
        self.patches[self.active].pdNum = pdNum
        self.patches[self.active].ok    = True
        name  = self.patches[self.active].name
        self.log.write("Registering number %s to %s" % (pdNum, name))
        
        reg = 'reg%i' % self.active
        self.Send([reg, pdNum])
        
        #set regWait to False. Patch is registered
        self.regWait = False
    
    def PdMessage(self, data):
        self.log.write("Message from PD:%s" % str(data))
    
    def Error(self, error):
        if error[0] == "print:":
            self.log.write("Print:%s" % str(error[1:]))
        elif error[0] == "oggcast~:":
            self.log.write("OggCast:%s" % str(error[1:]))
        else:
            self.log.write("PD:%s" % str(error))
    
    def PdStarted(self):
        self.log.write("PD has started")
    
    def PdDied(self):
        self.log.write("PD has died")
    
    def ComError(self, data):
        self.log.write("ComsError:%s" % str(error))
    

def main(args):
    
    #TODO: simple but effective. needs decent parsing tho.
    if args[1] == "-c":
        configFile = args[2]
    else:
        sys.exit(1)
    
    #create mixing/streaming patch
    puredata = PureData(configFile)
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
    main(sys.argv)
