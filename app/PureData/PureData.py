#!/usr/bin/env python

#Import Modules
import ConfigParser
from Pd import Pd
from time import time, sleep


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
    
    def debug(self, state):
        self.Send(['debug', state])
    
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
        self.Send(['open', patch.filename, patch.folder])
        
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
            self.Send(['reg', patch.channel, self.pdnum])
            self.pdnum = 0
        
        return loadError
    
    def activate_patch(self, patch):
        channel = patch.channel
        self.Send(["coms",channel, 'dsp', 1])
    
    def fade_in_patch(self, patch):
        channel = patch.channel
        self.Send(['volume', 'fade', self.fadeTime])
        self.Send(['volume', 'chan', channel])
        
        #pause while the fade occours
        self.pause(self.fadeTime)
    
    def stop_patch(self, patch):
        self.Send(["coms", patch.channel, 'dsp', 0])
        self.Send(['reg', patch.channel, 0])
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
                self.log.write("Error %d: %s" %(e.args[0], e.args[1]))
    


