#!/usr/bin/env python

from DbInterface import DbInterface
import ConfigParser
from time import sleep
import sys
import os


host = ''
user = ''
passwd = ''

database = ''

patchFolder = sys.argv[1]
dirList     = os.listdir(patchFolder)

dbi = DbInterface(user, passwd, database, host)

for dir in dirList:
    infoFile = os.path.join(patchFolder, dir, "info")

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
        if not author.exists():
            print ("Author %s doesn't exist, adding now" % authorname)
            author.set("link", weblink)
            author.create()
        else:
            print ("Author %s exists already, skipping" % authorname)
        
        patch = dbi.get_patch()
        patch.retreive_one("name", patchname)
        if not patch.exists():
            print ("Patch %s doesn't exist, adding now" % patchname)
            patch.set("aid", author.get("aid"))
            patch.create()
        else:
            print ("Author %s exists already, skipping" % authorname)

