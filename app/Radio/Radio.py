#!/usr/bin/env python

#Import Modules
import os
import sys
import shutil
import signal
from PatchFactory import PatchFactory
from DbInterface import Logger
import ConfigParser
from Pd import Pd
from time import time


class Radio():

    def __init__(self, options, dbI):
    
        self.config      = ConfigParser.SafeConfigParser()
        self.config.read(options.configfile)
        
        self.patchDir     = self.config.get('paths', 'patchDir')
        self.tempDir      = self.config.get('paths', 'tempDir')
        self.loadError    = False
        self.channel      = 1
        self.patches      = []
        self.maxchannels  = 2
        
        self.dbI          = dbI
        self.log          = Logger(self.dbI, options.verbose)
        self.PatchFactory = PatchFactory(self.patchDir, self.tempDir, self.dbI, self.log)
        
        self.radioInfo   = self.dbI.get_radio_info()
        
        #clears out the temp folder when starting up to remove anything from previous runs
        for tempFolder in os.listdir(self.tempDir):
            tempFolderPath = os.path.join(self.tempDir, tempFolder)
            try:
                if os.path.isfile(tempFolderPath):
                    os.remove(tempFolderPath)
            except Exception, e:
                self.log.write("Error %d: %s" %(e.args[0], e.args[1]))
                sys.exit(1)
                
        #create PD instance
        self.pd = PureData(options.configfile, self.log)
        
        if options.debug:
            self.pd.debug(1)
    
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
        pname = patch.data['name']
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
        
        for patch in self.patches:
            tempFolder = patch.folder
            if os.path.isdir(tempFolder):
                shutil.rmtree(tempFolder)
        
        #tell DB that program is down
        self.radioInfo.radio_status("down")
        self.log.write("Bye Bye")
        sys.exit(0)
    



