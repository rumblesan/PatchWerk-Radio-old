#!/usr/bin/env python

import MySQLdb
import ConfigParser
from time import sleep
import sys
import os


host = ''
user = ''
passwd = ''

database = ''


def update_author_info(db, author, link):

    cursor = db.cursor()
    authquery = """SELECT *
                   FROM authors
                   WHERE author = "%s"
            """ % author
    cursor.execute(authquery)
    row = cursor.fetchone()
    cursor.close()
    if row == None:
        query = """INSERT INTO authors
                   (author, link)
                   VALUES ("%s", "%s")
                """ % (author, link)
        cursor = db.cursor()
        cursor.execute(query)
        cursor.close()
        cursor = db.cursor()
        cursor.execute(authquery)
        row = cursor.fetchone()
        cursor.close()
    aid = row[0]
    return aid

def update_patch_info(db, patchname, authorid):

    cursor = db.cursor()
    query = """SELECT *
               FROM patches
               WHERE patchname = "%s"
            """ % patchname
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    if row != None:
        query = """UPDATE patches
                   SET patchname = "%s",
                       aid    = %i
                   WHERE patchname = "%s"
                """ % (patchname, authorid, patchname)
        cursor = db.cursor()
        cursor.execute(query)
        cursor.close()
    else:
        query = """INSERT INTO patches
                   (patchname, aid)
                   VALUES ("%s", %i)
                """ % (patchname, authorid)
        cursor = db.cursor()
        cursor.execute(query)
        cursor.close()


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

        authorid = update_author_info(db, author, link)
        update_patch_info(db, patchname, authorid)





