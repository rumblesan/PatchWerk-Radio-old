#!/usr/bin/env python

from DbInterface import DbInterface
import ConfigParser
import sys
import os
import shutil
import tarfile


host = ''
user = ''
passwd = ''
database = ''

patchFolder    = sys.argv[1]
downloadFolder = sys.argv[2]
patchComsFile  = os.path.join(patchFolder, "misc", "patchComs.pd")
dirList        = os.listdir(patchFolder)
dbi = DbInterface(user, passwd, database, host)


def CreateTar(patchname, patchDir, patchComsFile, downloadFolder):
        
        fileName = patchname.replace(" ", "-")
        tempdir  = os.path.join(os.getcwd(), fileName)

        patchComsDest = os.path.join(tempdir, "patchComs.pd")
        
        shutil.copytree(patchDir, tempdir)
        shutil.copyfile(patchComsFile, patchComsDest)
        
        tarName = fileName + ".tar.gz"
        tarDest = os.path.join(os.getcwd(), tarName)
        
        t = tarfile.open(tarName, mode = 'w:gz')
        t.add(tempdir, os.path.basename(tempdir))
        t.close()
        
        dlDest = os.path.join(downloadFolder, tarName)
        
        shutil.copyfile(tarName, dlDest)
        shutil.rmtree(tempdir)
        os.remove(os.path.join(os.getcwd(), tarName))
        
        return tarName
        

for dirname in dirList:
    patchDir = os.path.join(patchFolder, dirname)
    infoFile = os.path.join(patchDir, "info")

    if os.path.isfile(infoFile):
        patchInfo = ConfigParser.SafeConfigParser()
        patchInfo.read(infoFile)
        
        authorname = patchInfo.get('info', 'author')
        patchname  = patchInfo.get('info', 'title')
        weblink    = patchInfo.get('info', 'link')
        
        print (authorname, patchname, weblink)
        del(patchInfo)

        author = dbi.get_author()
        author.retreive_one("name", authorname)
        author.set("name", authorname)
        author.set("link", weblink)

        if not author.exists():
            print ("Author %s doesn't exist, adding now" % authorname)
            author.create()
        else:
            print ("Author %s exists already, updating" % authorname)
            author.update()
        
        dlfile = CreateTar(patchname, patchDir, patchComsFile, downloadFolder)
        
        patch = dbi.get_patch()
        patch.retreive_one("name", patchname)
        patch.set("name", patchname)
        patch.set("aid", author.get("aid"))
        patch.set("dlfile", dlfile)

        if not patch.exists():
            print ("Patch %s doesn't exist, adding now" % patchname)
            patch.create()
        else:
            print ("Patch %s exists already, Updating" % patchname)
            patch.update()

        del(author)
        del(patch)


