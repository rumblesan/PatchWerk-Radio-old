#!/usr/bin/env python

#Import Modules
import os
import re
import sys
import shutil
import random
import signal
import MySQLdb
import ConfigParser
from Pd import Pd
from time import time, strftime

class DbInterface():
    
    def __init__(self, user, passwd, db, host="localhost"):
        try:
            self.db = MySQLdb.connect(host=host,
                                      user=user,
                                      passwd=passwd,
                                      db=db)
        except MySQLdb.Error, e:
            print "Error %d: %s" %(e.args[0], e.args[1])
            sys.exit(1)
        
        self.logging   = "logs"
        self.control   = "control"
        self.patchInfo = "patchInfo"
        self.playing   = "playing"
        
    def write_log(self, logEntry):
        timestamp, message = logEntry
        cursor = self.db.cursor()
        query = """INSERT INTO %s
                   (message)
                   VALUES ("%s")
        """ % (self.logging, message)
        cursor.execute(query)
        cursor.close()

        
    def control_state(self):
        cursor = self.db.cursor()
        query = "SELECT state FROM %s" % self.control
        cursor.execute(query)
        row = cursor.fetchone()
        state = row[0]
        cursor.close()
        return state
    
    def patch_plays(self, patchName):
        cursor = self.db.cursor()
        query = """SELECT name, playNum
                   FROM %s
                   WHERE name = "%s"
        """ % (self.patchInfo, patchName)
        cursor.execute(query)
        row = cursor.fetchone()
        
        if row == 0:
            query = """INSERT INTO %s
                       (name, playNum)
                       VALUES ("%s",%i)
            """ % (self.patchInfo, patchName, 1)
        else:
            playNum = row[1] + 1
            query = """UPDATE %s
                       SET playNum = %i
                       WHERE name = "%s"
            """ % (self.patchInfo, playNum, patchName)
        
        cursor.execute(query)
        cursor.close()
    
    def currently_playing(self, patchName):
        cursor = self.db.cursor()
        query = "SELECT current FROM %s" % self.playing
        cursor.execute(query)
        row = cursor.fetchone()
        current  = row[0]
        previous = row[1]
        query = """UPDATE %s
                   SET current = "%s"
                   SET previous = "%s"
                   WHERE name = "%s"
                   AND   name = "%s"
        """ % (self.patchInfo, patchName, current, current, previous)

        cursor.execute(query)
        cursor.close()


class LoggingObj():
    #class to handle logging. prepends timestamp to data then prints it out
    
    def __init__(self, logdb=None):
        self.header()
        self.logdb = logdb

    def write(self, logLine):
        output = (self.timeStamp(), logLine)
        if self.logdb:
            print "%s   %s" % output
            self.logdb.write_log(output)
        else:
            print "%s   %s" % output
    
    def timeStamp(self):
        return strftime("%Y%m%d %H:%M:%S")
    
    def header(self):
        print "\n*******************\nStartingUp\n*******************\n"
    

class SubPatch():
    #Class for holding information about sub patches
    
    def __init__(self, number):
        self.name    = "patch%i" % number
        self.folder  = ""
        self.patch   = ""
        self.pdNum   = 0
        self.ok      = False
        self.title   = ""
        self.author  = ""
        self.info    = ""
        self.tempDir = ""
        
    def read_info_file(self):
        infoFile = os.path.join(self.tempDir, "info")
        if not os.path.isfile(infoFile):
            self.title  = ""
            self.author = ""
            self.info   = ""
        else:
            config      = ConfigParser.SafeConfigParser()
            config.read(infoFile)
            self.title  = self.config.get('info', 'title')
            self.author = self.config.get('info', 'author')
            self.info   = self.config.get('info', 'info')
    

class PureData(Pd):
    #Class that interfaces with PD process
    def __init__(self, configFile):
        
        self.patch   = 'masterPatch.pd'
        
        self.config      = ConfigParser.SafeConfigParser()
        self.config.read(configFile)
        
        dbUser           = self.config.get('database', 'user')
        dbPasswd         = self.config.get('database', 'password')
        dbHost           = self.config.get('database', 'host')
        dbName           = self.config.get('database', 'dbname')
        self.db          = DbInterface(dbUser, dbPasswd, dbName, dbHost)
        
        self.log         = LoggingObj(self.db)
        
        self.active      = 2
        self.old         = 1
        
        self.patches     = {1:SubPatch(1), 2:SubPatch(2)}
        
        comPort          = self.config.getint('puredata', 'comPort')
        
        self.fadeTime    = self.config.getint('puredata', 'fadeTime')
        self.playTime    = self.config.getint('puredata', 'playTime')
        
        gui              = False
        
        self.regWait     = False
        self.regTimeout  = 20
        self.loadError   = False
        self.connection  = False
        
        self.fileMatch   = re.compile("^main-.*?\.pd$")
        
        extras           = "-alsa"
        
        self.patchDir    = self.config.get('paths', 'patchDir')
        self.masterDir   = self.config.get('paths', 'masterDir')
        self.tempDir     = self.config.get('paths', 'tempDir')
        path             = [self.masterDir]
        
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
        
        password     = self.config.get('streaming', 'password')
        
        hostInfo     = [self.config.get('streaming', 'host')]
        hostInfo.append(self.config.get('streaming', 'mountPoint'))
        hostInfo.append(self.config.get('streaming', 'streamport'))
        
        settings     = [self.config.get('streaming', 'samplerate')]
        settings.append(self.config.get('streaming', 'channels'))
        settings.append(self.config.get('streaming', 'maxBitrate'))
        settings.append(self.config.get('streaming', 'nomBitrate'))
        settings.append(self.config.get('streaming', 'minBitrate'))
        
        meta                = {}
        meta['ARTIST']      = self.config.get('meta', 'artist')
        meta['TITLE']       = self.config.get('meta', 'title')
        meta['DESCRIPTION'] = self.config.get('meta', 'description')
        meta['GENRE']       = self.config.get('meta', 'genre')
        meta['LOCATION']    = self.config.get('meta', 'location')
        meta['COPYRIGHT']   = self.config.get('meta', 'copyright')
        meta['CONTACT']     = self.config.get('meta', 'contact')
        
        
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
        
    def control_check(self):
        self.log.write("Checking control state")
        while self.db.control_state() == "pause":
            self.log.write("Control State is paused. Not Loading patch")
            self.log.write("Pausing for 60 seconds")
            self.pause(60)
    
    def switch_patch(self):
        #change the active patch number
        self.old, self.active = self.active, self.old
        name = "patch%i" % self.active
        self.log.write("Changing active patch to be %s" % name)
    
    def create_new_patch(self):
        
        self.loadError = False
        name = self.patches[self.active].name
        
        #get a random patch from the patch folder
        patch, folder = self.get_random_patch()
        patchFolder   = os.path.join(self.patchDir, folder)
        tempFolder    = os.path.join(self.tempDir, name)
        
        self.log.write("Loading new patch for %s" % name)
        
        #update patch object in active slot
        self.patches[self.active].patch   = patch
        self.patches[self.active].folder  = folder
        self.patches[self.active].tempDir = tempFolder
        
        #copy the patch folder into a temporary folder
        #the patch will be opened from this location
        shutil.copytree(patchFolder, tempFolder)
        
        #read the data in the new patch info file
        self.patches[self.active].read_info_file()
        
        self.log.write("New Patch is %s" % patch)
        self.Send(['open', patch, tempFolder])
        
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
        
        #get the name of the previously loaded patch
        previousPatch = self.patches[self.old].patch
        
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
                checkDir     = os.path.join(self.patchDir, patchFolder)
                #TODO: want to put a check in here for the directory name
                if os.path.isdir(checkDir):
                    dirFound = True
                else:
                    self.log.write("Error:%s is not a valid folder" % checkDir)
            
            #suitable folder chosen, now check for main patch inside it
            fileList = os.listdir(checkDir)
            for file in fileList:
                if self.fileMatch.search(file):
                    patchFile = file
                    mainFound = True
                    
            
            if not mainFound:
                self.log.write("Error:%s has no main patch" % checkDir)
                dirFound = False
            elif patchFile == previousPatch:
                self.log.write("Error:%s also the previous patch" % patchFile)
                dirFound = False
            else:
                #this patch is ok, stop the loop
                self.log.write("Chosen %s as new patch" % patchFile)
                patchFound = True
            
            if not patchFound:
                self.log.write("Choosing again.")
        
        return (patchFile, patchFolder)
    
    def load_error(self):
        #notifies when there has been an error loading a patch
        patch  = self.patches[self.active].patch
        folder = self.patches[self.active].folder
        
        self.log.write("Error:***************************************")
        self.log.write("Error:Problem loading %s from %s" % (patch, folder))
        self.log.write("Error:Unloading patch and starting again")
        
        self.Send(['close', patch])
    
    def activate_patch(self):
        #turn on DSP in new patch
        self.log.write("Turning on %s DSP" % self.patches[self.active].name)
        self.Send(["coms",self.active, 'dsp', 1])
        if self.patches[self.active].title != "":
            self.db.patch_plays(self.patches[self.active].title)
            self.db.currently_playing(self.patches[self.active].title)
        else:
            self.db.currently_playing("No Info")
        self.pause(1)
    
    def crossfade(self):
        #fade across to new active patch
        self.log.write("Fading over to %s" % self.patches[self.active].name)
        
        self.Send(['volume', 'fade', self.fadeTime])
        
        self.Send(['volume', 'chan', self.active])
        
        #pause while the fade occours
        self.pause(self.fadeTime)
    
    def kill_old_patch(self):
        #disconnect old patch from master patch and then del the object
        name  = self.patches[self.old].name
        if self.patches[self.old].ok:
            self.log.write("Stopping %s" % name)
            
            self.Send(["coms", self.old, 'dsp', 0])
            
            self.Send(["register", self.old, 0])
            
            self.pause(1)
            
            self.Send(['close', self.patches[self.old].patch])
            
            #deleting temporary file
            tempFolder = os.path.join(self.tempDir, name)
            shutil.rmtree(tempFolder)
            
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
        
        self.Send(["register", self.active, pdNum])
        
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
    
    def terminate(self, signum, frame):
        #called when a SIGTERM is received
        #will deal with:- disconnecting the stream
        #                 shutting down PD nicely
        #                 exit python
        self.log.write("Received SIGTERM")
        self.log.write("Disconnecting Stream")
        self.Send(["stream", "connect", 0])
        if self.Alive():
            self.log.write("Killing PureData Process")
            self.Exit()
        #TODO: this needs to check for the old temp patch as well
        #      and delete it if it exists
        name  = self.patches[self.active].name
        tempFolder = os.path.join(self.tempDir, name)
        shutil.rmtree(tempFolder)
        self.log.write("Bye Bye")
        sys.exit(0)
    
    def PdStarted(self):
        self.log.write("PD has started")
    
    def PdDied(self):
        self.log.write("PD has died")
    
    def ComError(self, data):
        self.log.write("ComsError:%s" % str(error))
    

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
    
    #create mixing/streaming patch
    puredata = PureData(configFile)
    puredata.pause(1)
    
    #register handler for SIGTERM
    signal.signal(signal.SIGTERM, puredata.terminate)
    
    #check that pure data is running fine
    puredata.check_alive()
    
    #check that Python and PD are connected
    puredata.check_network()
    
    #Turn on DSP for pure data
    puredata.Send(['dsp', 1])
    
    #start streaming
    puredata.streaming_setup()
    
    while True:
        #check to see if the control state is paused or not
        puredata.control_check()
        
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
