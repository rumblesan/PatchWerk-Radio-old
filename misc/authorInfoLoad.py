#!/usr/bin/env python

import MySQLdb
import ConfigParser
from time import sleep
import sys
import os



def update_author_info(db, author, link):

    cursor = db.cursor()
    query = """SELECT *
               FROM authorinfo
               WHERE author = "%s"
            """ % author
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    if row == None:
        query = """INSERT INTO authorinfo
                   (author, link)
                   VALUES ("%s", "%s")
                """ % (author, link)
        cursor = db.cursor()
        cursor.execute(query)
        cursor.close()


def update_patch_info(db, patchname, author):

    cursor = db.cursor()
    query = """SELECT *
               FROM patchinfo
               WHERE patchname = "%s"
            """ % patchname
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    if row != None:
        query = """UPDATE patchinfo
                   SET patchname = "%s",
                       author    = "%s"
                   WHERE patchname = "%s"
                """ % (patchname, author, patchname)
        cursor = db.cursor()
        cursor.execute(query)
        cursor.close()
    else:
        query = """INSERT INTO patchinfo
                   (patchname, author)
                   VALUES ("%s", "%s")
                """ % (patchname, author)
        cursor = db.cursor()
        cursor.execute(query)
        cursor.close()


host = ''
user = ''
passwd = ''

database = ''

try:
    db = MySQLdb.connect(host, user, passwd)
except MySQLdb.Error, e:
    print "Error %d: %s" %(e.args[0], e.args[1])
    sys.exit(1)

print 'Connected'

query = "USE %s" % database
cursor = db.cursor()
cursor.execute(query)
cursor.close()

patchFolder = sys.argv[1]
dirList     = os.listdir(patchFolder)

for dir in dirList:
    infoFile = os.path.join(patchFolder, dir, "info")

    if os.path.isfile(infoFile):
        patchInfo = ConfigParser.SafeConfigParser()
        patchInfo.read(infoFile)
        
        author    = patchInfo.get('info', 'author')
        patchname = patchInfo.get('info', 'title')
        link      = patchInfo.get('info', 'link')
        
        print (author, patchname, link)
        del(patchInfo)

        update_patch_info(db, patchname, author)
        update_author_info(db, author, link)





