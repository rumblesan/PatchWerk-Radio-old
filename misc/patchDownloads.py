#!/usr/bin/env python

import MySQLdb
import ConfigParser
from time import sleep
import sys
import os
import shutil
import tarfile



host = 'localhost'
user = 'patchwerk'
passwd = 'radio!stats'
database = 'patchwerk'


patchesFolder  = sys.argv[1]
downloadFolder = sys.argv[2]
patchComsFile  = sys.argv[3]

dirList     = os.listdir(patchesFolder)

for dirName in dirList:
    patchDir = os.path.join(patchesFolder, dirName)
    infoFile = os.path.join(patchDir, "info")

    if os.path.isfile(infoFile):
        patchInfo = ConfigParser.SafeConfigParser()
        patchInfo.read(infoFile)
        patchname = patchInfo.get('info', 'title')
        print patchname
        del(patchInfo)

        fileName = patchname.replace(" ", "-")
        tempdir = os.path.join(os.getcwd(), fileName)

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





