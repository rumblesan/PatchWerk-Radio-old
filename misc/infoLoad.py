#!/usr/bin/env python

from DbInterface import DbInterface
import ConfigParser
import sys
import os
import shutil
import tarfile
from optparse import OptionParser


parser = OptionParser()
parser.add_option('-h', '--host', action='store', dest='host',
                  default='localhost', help='Host the DB runs on')
parser.add_option('-u', '--user', action='store', dest='user',
                  help='The user to connect to the database as')
parser.add_option('-p', '--pass', action='store', dest='passwd',
                  help='The password of the db user')
parser.add_option('-d', '--dbname', action='store', dest='dbname',
                  help='The database name')

parser.add_option('-P', '--patch', action='store', dest='patchfolder',
                  help='The folder containing the patches')
parser.add_option('-D', '--download', action='store', dest='dlfolder',
                  help='The download folder the patches go in')
(opts, args) = parser.parse_args()

mandatories = ['host', 'user', 'passwd', 'dbname', 'patchfolder', 'dlfolder']

for m in mandatories:
    if not opts.__dict__[m]:
        print "Mandatory option missing\n"
        parser.print_help()
        exit(-1)

patchComsFile  = os.path.join(opts.patchfolder, "misc", "patchComs.pd")
dirList        = os.listdir(opts.patchfolder)

try:
    dbi = DbInterface(opts.user, opts.passwd, opts.dbname, opts.host)
except MySQLdb.Error, e:
    print "Error %d: %s" %(e.args[0], e.args[1])
    sys.exit(1)


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
    patchDir = os.path.join(opts.patchfolder, dirname)
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
        
        dlfile = CreateTar(patchname, patchDir, patchComsFile, opts.dlfolder)
        
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


