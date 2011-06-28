#!/usr/bin/env python

#Import Modules
import os
import re
import sys
import shutil
import random
import signal
from DbInterface import DbInterface
from DbInterface import Patch
from DbInterface import Logger
import ConfigParser
from Pd import Pd
from time import time


class PatchFactory:
    #class that will deal with getting
    #random patches and returning a SubPatchObject

    def __init__(self, patchDir, tempDir, dbI, logger):
        self.dbI       = dbI
        self.patchDir  = patchDir
        self.tempDir   = tempDir
        self.prevPatch = ''
        self.log       = logger
        
        self.fileMatch   = re.compile("^main-.*?\.pd$")
    
    def get_random_patch(self):
        #get a random patch from the patch directory
        
        #get a list of files from the patch directory
        dirList       = os.listdir(self.patchDir)
        
        patchFound    = False
        dirFound      = False
        mainFound     = False
        
        #keep looping untill a suitable next patch is found
        while not patchFound:
            #keep going until a valid directory is found
            while not dirFound:
                patchFolder = random.choice(dirList)
                checkDir    = os.path.join(self.patchDir, patchFolder)
                #TODO: want to put a check in here for the directory name
                if os.path.isdir(checkDir):
                    dirFound = True
                else:
                    self.log.write("Error:%s is not a valid folder" % checkDir)
            
            #suitable folder chosen, now check for main patch inside it
            for patchFile in os.listdir(checkDir):
                if self.fileMatch.search(patchFile):
                    mainFound = True
                    
            if not mainFound:
                self.log.write("Error:%s has no main patch" % checkDir)
                dirFound = False
            elif patchFile == self.prevPatch:
                self.log.write("Error:%s also the previous patch" % patchFile)
                dirFound = False
            else:
                #this patch is ok, stop the loop
                self.log.write("Chosen %s as new patch" % patchFile)
                patchFound = True
            
            if not patchFound:
                self.log.write("Choosing again.")
        
        self.prevPatch = patchFile
        return (patchFile, patchFolder)
    
    def new_patch(self):
        #get a random patch from the patch folder
        file, folder = self.get_random_patch()
        patchFolder  = os.path.join(self.patchDir, folder)
        tempFolder   = os.path.join(self.tempDir, file)
        
        #copy the patch folder into a temporary folder
        #the patch will be opened from this location
        shutil.copytree(patchFolder, tempFolder)
        
        #create patch object
        newPatch = SubPatch(file, tempFolder, self.dbI)
        
        self.log.write("New Patch is %s" % newPatch.get('name'))
        
        return newPatch
    

class SubPatch(Patch):
    #Class for holding information about sub patches

    def __init__(self, filename, folder, dbI):
        Patch.__init__(self, dbI)
        self.filename = filename
        self.folder   = folder
        self.channel  = -1
        self.pdnum    = -1
        self.read_info_file()
    
    def read_info_file(self):
        infoFile = os.path.join(self.folder, "info")
        if os.path.isfile(infoFile):
            config      = ConfigParser.SafeConfigParser()
            config.read(infoFile)
            title  = config.get('info', 'title')
            del(config)
            self.retreive_one('title', title)
    

class Radio():

    def __init__(self, configFile, dbI):
    
        self.config      = ConfigParser.SafeConfigParser()
        self.config.read(configFile)
        
        self.patchDir     = self.config.get('paths', 'patchDir')
        self.tempDir      = self.config.get('paths', 'tempDir')
        self.loadError    = False
        self.channel      = 1
        self.patches      = []
        self.maxchannels  = 2
        
        self.dbI          = dbI
        self.log          = Logger(self.dbI)
        self.PatchFactory = PatchFactory(self.patchDir, self.tempDir, self.dbI, self.log)
        
        self.radioInfo   = self.dbI.get_radio_info()
        
        #clears out the temp folder when starting up to remove anything from previous runs
        for tempFolder in os.listdir(self.tempDir):
            tempFolderPath = os.path.join(self.tempDir, tempFolder)
            try:
                if os.path.isfile(tempFolderPath):
                    os.remove(tempFolderPath)
            except Exception, e:
                print e
                sys.exit(1)
                
        #create PD instance
        self.pd = PureData(configFile, self.log)
    
    def pause(self, length):
        self.pd.pause(length)
    
    def play(self):
        self.pd.play()
    
    def check_pd(self):
        if self.pd.Alive:
            self.log.write('PD started fine')
        else:
            self.log.write('Problem starting PD')
            return False
        
        self.log.write('Waiting for PD to register the connection')
        wait = 0
        while not self.pd.connection:
            self.pause(1)
            wait += 1
            if wait > 20:
                self.log.write('Problem connecting to PD')
                return False
        return True
    
    def all_ok(self):
        #everything is loaded fine. set status to up in db
        #and turn on PD DSP
        self.radioInfo.radio_status("up")
        self.pd.dspstate(1)
    
    def streaming_setup(self):
        #send a message to the streaming controls in the master patch
        self.log.write("Setting up streaming")
        self.pd.streaming_setup(self.config)
    
    def control_check(self):
        self.log.write("Checking control state")
        while self.radioInfo.get("loading") != "on":
            self.log.write("Loading patches is turned off")
            self.log.write("Pausing for 60 seconds")
            self.pause(60)
    
    def new_patch(self):
        newPatch         = self.PatchFactory.new_patch()
        newPatch.channel = self.channel
        self.patches.insert(0, newPatch)
        if self.pd.load_patch(newPatch):
            #there's been a loading error
            self.loadError = True
        else:
            self.loadError = False
            self.channel += 1
            if self.channel > self.maxchannels:
                self.channel = 1
            
        return self.loadError
    
    def loading_error(self):
        #notifies when there has been an error loading a patch
        patch = self.patches.pop()
        self.log.write("Error:***************************************")
        self.log.write("Error:Problem loading %s from %s" % (patch.get('name'), patch.folder))
        self.log.write("Error:Unloading patch and starting again")
        
        self.pd.stop_patch(patch)
        shutil.rmtree(patch.folder)
    
    def activate_patch(self):
        #turn on DSP in new patch
        patch = self.patches[0]
        self.log.write("Turning on %s DSP" % patch.get('name'))
        self.pd.activate_patch(patch)
        
        patch.played()
        self.radioInfo.new_patch(patch.get('name'))
        self.pause(1)
    
    def crossfade(self):
        #fade across to new active patch
        patch = self.patches[0]
        self.log.write("Fading over to %s" % patch.get('name'))
        self.pd.fade_in_patch(patch)
    
    def kill_old_patch(self):
        #disconnect old patch from master patch and then del the object
        if len(self.patches) == self.maxchannels:
            patch  = self.patches.pop()
            
            self.log.write("Stopping %s" % patch.get('name'))
            self.pd.stop_patch(patch)
            
            #deleting temporary file
            shutil.rmtree(patch.folder)
        else:
            self.log.write("Not yet at max number of patches")
    
    def terminate(self, signum, frame):
        #called when a SIGTERM is received
        #will deal with:- disconnecting the stream
        #                 shutting down PD nicely
        #                 exit python
        self.log.write("Received SIGTERM")
        self.log.write("Disconnecting Stream")
        
        self.pd.shut_down()
        
        for patches in self.patches
            tempFolder = os.path.join(patch.folder, patch.filename)
            if os.path.isdir(tempFolder):
                shutil.rmtree(tempFolder)
        
        #tell DB that program is down
        self.db.current_state("down")
        self.log.write("Bye Bye")
        sys.exit(0)
    

class PureData(Pd):
    #Class that interfaces with PD process
    def __init__(self, configFile, logger):
        
        self.patch       = 'masterPatch.pd'
        
        config           = ConfigParser.SafeConfigParser()
        config.read(configFile)
        
        self.log         = logger
        
        comPort          = config.getint('puredata', 'comPort')
        
        self.fadeTime    = config.getint('puredata', 'fadeTime')
        self.playTime    = config.getint('puredata', 'playTime')
        
        gui              = False
        self.regWait     = False
        self.pdnum      = 0
        self.regTimeout  = 20
        self.connection  = False
        
        extras           = "-alsa"
        
        self.masterDir   = config.get('paths', 'masterDir')
                
        path             = [self.masterDir]
        
        Pd.__init__(self, comPort, gui, self.patch, extra=extras, path=path)
        self.log.write("Starting PD Process:%s" % self.argLine)
    
    def PdStarted(self):
        self.log.write("PD has started")
    
    def PdDied(self):
        self.log.write("PD has died")
    
    def ComError(self, data):
        self.log.write("ComsError:%s" % str(error))
    
    def Pd_connection(self, data):
        type = data[0]
        val  = data[1]
        if type == "status":
            if val == "1":
                self.log.write('Network connection to PD is up')
                self.connection = True
    
    def Pd_register(self, data):
        #Gets the unique number from the PD subPatch
        #This is sent to the Master Patch to change send and receieve
        #   objects so that the two can communicate
        self.pdnum = data[0]
        
        #set regWait to False. Patch is registered
        self.regWait = False
    
    def pause(self, pauseLength):
        #pause for a specified number of seconds
        #will keep updating the master patch and sub patches
        #so that network communication still works
        start = time()
        while time() - start < pauseLength:
            self.Update()

    def play(self):
        self.pause(self.playTime)
    
    def dspstate(self, state):
        self.Send(['dsp', state])
    
    def streaming_setup(self, config):
        password     = config.get('streaming', 'password')
        
        hostInfo = []
        hostInfo.append(config.get('streaming', 'host'))
        hostInfo.append(config.get('streaming', 'mountPoint'))
        hostInfo.append(config.get('streaming', 'streamport'))
        
        settings = []
        settings.append(config.get('streaming', 'samplerate'))
        settings.append(config.get('streaming', 'channels'))
        settings.append(config.get('streaming', 'maxBitrate'))
        settings.append(config.get('streaming', 'nomBitrate'))
        settings.append(config.get('streaming', 'minBitrate'))
        
        meta                = {}
        meta['ARTIST']      = config.get('meta', 'artist')
        meta['TITLE']       = config.get('meta', 'title')
        meta['DESCRIPTION'] = config.get('meta', 'description')
        meta['GENRE']       = config.get('meta', 'genre')
        meta['LOCATION']    = config.get('meta', 'location')
        meta['COPYRIGHT']   = config.get('meta', 'copyright')
        meta['CONTACT']     = config.get('meta', 'contact')
        
        #set the server type to Icecast2
        self.Send(["stream", "server", 1])
        
        #send stream META Data
        for tag, info in meta.iteritems():
            self.Send(["stream", "meta", tag, info])
        
        self.Send(["stream", "password", password])
        
        self.log.write("HostInfo is %s" % str(hostInfo))
        self.Send(["stream", "hostinfo", " ".join(hostInfo)])
        
        self.log.write("Stream Info is %s" % str(settings))
        self.Send(["stream", "settings", " ".join(settings)])
        
        self.log.write("Attempting connection to Icecast")
        self.Send(["stream", "connect", 1])
    
    def load_patch(self, patch):
        file   = patch.filename
        folder = patch.folder
        self.Send(['open', file, folder])
        
        #change regWait to true. We will wait untill the patch is registered
        self.regWait = True
        loadError = False
        #pause until the patch registers
        #if it doesn't register in a certain time
        #then we have a problem
        errCount = 0
        while self.regWait:
            self.pause(1)
            errCount += 1
            if errCount > self.regTimeout:
                loadError = True
                break
        
        if self.pdnum == 0:
            loadError = True
        
        if not loadError:
            patch.pdnum = self.pdnum
            self.log.write("Registering number %s to %s" % (self.pdnum, patch.get('name')))
            
            self.Send(["register", patch.pdnum, self.pdnum])
            self.pdnum = 0
        
        return loadError
    
    def activate_patch(self, patch):
        patchNum = patch.pnum
        self.Send(["coms",patchNum, 'dsp', 1])
    
    def fade_in_patch(self, patch):
        patchNum = patch.pnum
        self.Send(['volume', 'fade', self.fadeTime])
        self.Send(['volume', 'chan', patchNum])
        
        #pause while the fade occours
        self.pause(self.fadeTime)
    
    def stop_patch(self, patch):
        self.Send(["coms", patch.pnum, 'dsp', 0])
        self.Send(["register", patch.pnum, 0])
        self.pause(1)
        self.Send(['close', patch.filename])
    
    def PdMessage(self, data):
        self.log.write("Message from PD:%s" % str(data))
    
    def Error(self, error):
        if error[0] == "print:":
            self.log.write("Print:%s" % str(error[1:]))
        elif error[0] == "oggcast~:":
            self.log.write("OggCast:%s" % str(error[1:]))
        else:
            self.log.write("PD:%s" % str(error))
    
    def shut_down(self):
        self.Send(["stream", "connect", 0])
        if self.Alive():
            self.log.write("Killing PureData Process")
            try:
                self.Exit()
            except OSError, e:
                print "Error %d: %s" %(e.args[0], e.args[1])
    

def main(args):
    
    if len(args) != 3:
        print "Too many Arguments. %i given" % len(args)
        sys.exit(1)
    elif args[1] != "-c":
        print "Incorrect Arg. Exepected -c but got %s" % len(args)
        sys.exit(1)
    elif not os.path.isfile(args[2]):
        print "File %s does not exist" % args[2]
        sys.exit(1)
    else:
        configFile = args[2]
    
    config   = ConfigParser.SafeConfigParser()
    config.read(configFile)
    dbUser   = config.get('database', 'user')
    dbPasswd = config.get('database', 'password')
    dbHost   = config.get('database', 'host')
    dbName   = config.get('database', 'dbname')
    dbI      = DbInterface(dbUser, dbPasswd, dbName, dbHost)
    del(config)
    
    #create mixing/streaming patch
    radio = Radio(configFile, dbI)
    radio.pause(1)
    
    #register handler for SIGTERM
    signal.signal(signal.SIGTERM, radio.terminate)

    #register handler for SIGTERM
    signal.signal(signal.SIGINT, radio.terminate)
    
    #check that pure data is running fine
    if radio.check_pd():
        #register status with DB and turn DSP on
        radio.all_ok()
    else:
        sys.exit(1)
    
    #start streaming
    radio.streaming_setup()
    
    while True:
        #check to see if the control state is paused or not
        radio.control_check()

        #tell master PD to create the new patch
        radio.new_patch()
        
        if radio.loadError:
            #call function to deal with loading error
            radio.load_error()
            
        else:
            #turn the DSP in the new patch on
            radio.activate_patch()
            
            #fade over to new patch
            radio.crossfade()
            
            #kill off old patch
            radio.kill_old_patch()
            
            #pause untill next patch needs to be loaded
            radio.play()

if __name__ == "__main__":
    main(sys.argv)
