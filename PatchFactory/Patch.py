#!/usr/bin/env python

#Import Modules
import re
import random
import ConfigParser

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
                    break
                    
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
        tempFolder   = os.path.join(self.tempDir, folder)
        
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
            self.retreive_one('name', title)
    