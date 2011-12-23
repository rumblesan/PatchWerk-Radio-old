#!/usr/bin/env python

#import modules
import MySQLdb
import MySQLdb.cursors
import sys
from time import strftime

class DbInterface():

    def __init__(self, user, passwd, db, host):
        try:
            self.db = MySQLdb.connect(host=host,
                                      user=user,
                                      passwd=passwd,
                                      db=db,
                                      cursorclass=MySQLdb.cursors.DictCursor)
        except MySQLdb.Error, e:
            print "Error %d: %s" %(e.args[0], e.args[1])
            sys.exit(1)
    
    def __del__(self):
        self.db.close()
    
    def get_patch(self, pid=''):
        patch = Patch(self, pid)
        return patch
        
    def get_author(self, aid=''):
        author = Author(self, aid)
        return author
    
    def get_logger(self, echo=False):
        logger = Logger(self, echo)
        return logger
    
    def get_radio_info(self):
        logger = RadioInfo(self, 1)
        return logger
    

class Model():

    def __init__(self, key, table, dbI):
        self.data   = {}
        self.key    = key
        self.table  = table
        self.dbI    = dbI
        self.cursor = self.dbI.db.cursor()
    
    def __del__(self):
        self.cursor.close()
    
    def get(self, key):
        return self.data[key]
    
    def set(self, key, value):
        if key in self.data:
            self.data[key] = value
    
    def exists(self, checkdb=False):
        keyval = self.data[self.key]
        if self.data[self.key] < 1:
            return False
        elif not checkdb:
            return True
        else:
            sql = """SELECT 1
                     FROM `%s`
                     WHERE `%s` = "%s"
                  """ % (self.table, self.key, keyval)

            try:
                self.cursor.execute(sql)
            except MySQLdb.Error, e:
                print "Error with mysql writing to DB, sql was: %s" % sql

            row = self.cursor.fetchone()
            if row != None:
                return True
            else:
                return False
    
    def dump_info(self):
        for col, value in self.data.iteritems():
            print "%s: %s" % (col.ljust(15), value)
    
    def retreive(self, value):
        sql = """SELECT *
                 FROM `%s`
                 WHERE `%s` = "%s"
              """ % (self.table, self.key, value)
        try:
            self.cursor.execute(sql)
        except MySQLdb.Error, e:
            print "Error with mysql writing to DB, sql was: %s" % sql
        row = self.cursor.fetchone()
        if row != None:
            for col, value in row.iteritems():
                self.data[col] = value
    
    def retreive_one(self, key, value):
        if key in self.data:
            sql = """SELECT *
                     FROM `%s`
                     WHERE `%s` = "%s"
                  """ % (self.table, key, value)
            try:
                self.cursor.execute(sql)
            except MySQLdb.Error, e:
                print "Error with mysql writing to DB, sql was: %s" % sql
            row = self.cursor.fetchone()
            if row != None:
                for col, value in row.iteritems():
                    self.data[col] = value
    
    def update(self):
        colvals = []
        keyval = self.data[self.key]
        for col, value in self.data.iteritems():
            colvals.append(""" `%s` = '%s' """ % (col, value))
        args = ", ".join(colvals)
        sql = """UPDATE `%s`
                 SET %s
                 WHERE `%s` = %i
              """ % (self.table, args, self.key, keyval)
        try:
            self.cursor.execute(sql)
        except MySQLdb.Error, e:
            print "Error with mysql writing to DB, sql was: %s" % sql

    def delete(self):
        keyval = self.data[self.key]
        sql = """DELETE FROM `%s`
                 WHERE `%s` = %i""" % (self.table, self.key, keyval)
        try:
            self.cursor.execute(sql)
        except MySQLdb.Error, e:
            print "Error with mysql writing to DB, sql was: %s" % sql
    
    def create(self):
        cols = []
        vals = []
        keyval = self.data[self.key]
        for col, value in self.data.iteritems():
            cols.append("""`%s`""" % col)
            vals.append("""'%s'""" % value)
        colargs = ", ".join(cols)
        valargs = ", ".join(vals)
        sql = """INSERT INTO `%s`
                 (%s)
                 VALUES (%s)
              """ % (self.table, colargs, valargs)
        try:
            self.cursor.execute(sql)
        except MySQLdb.Error, e:
            print "Error with mysql writing to DB, sql was: %s" % sql
        self.retreive(self.cursor.lastrowid)
    

class Patch(Model):

    def __init__(self, dbI, pid=0):
        Model.__init__(self, "pid", "patches", dbI)
        self.data['pid']    = 0
        self.data['name']   = ''
        self.data['plays']  = 0
        self.data['aid']    = 0
        self.data['dlfile'] = ''
        if (pid > 0):
            self.retreive(pid)
    
    def get_author(self):
        if self.data['aid'] > 0:
            author = self.dbI.get_author(self.data['aid'])
            return author
            
    def played(self):
        playnum = self.get("plays")
        playnum += 1
        self.set("plays", playnum)
        self.update
    

class Author(Model):

    def __init__(self, dbI, aid=0):
        Model.__init__(self, "aid", "authors", dbI)
        self.data['aid']    = 0
        self.data['name'] = ''
        self.data['link']   = ''
        if (aid > 0):
            self.retreive(aid)
    
    def get_patches(self):
        if self.data['aid'] > 0:
            # add functionality here
            # will return list of Patch objects
            pass
    

class RadioInfo(Model):

    def __init__(self, dbI, id=0):
        Model.__init__(self, "id", "radio", dbI)
        self.data['id']       = 0
        self.data['status']   = ''
        self.data['loading']  = ''
        self.data['playing']  = ''
        self.data['previous'] = ''
        if (id > 0):
            self.retreive(id)
    
    def new_patch(self, patchname):
        playing = self.get("playing")
        self.set("previous", playing)
        self.set("playing", patchname)
        self.update()

    def radio_status(self, status):
        self.set("status", status)
        self.update()

class Logger():
    
    def __init__(self, dbI, echo=False):
        self.dbI    = dbI
        self.cursor = self.dbI.db.cursor()
        self.echo   = echo
        self.table  = "logs"
    
    def write(self, logLine):
        output = (self.timeStamp(), logLine)
        self.write_log(output)
        if self.echo:
            print "%s   %s" % output
    
    def write_log(self, logEntry):
        timestamp, message = logEntry
        query = """INSERT INTO %s
                   (message)
                   VALUES ("%s")
                """ % (self.table, message)
        try:
            self.cursor.execute(query)
        except MySQLdb.Error, e:
            print "Error with mysql writing to DB, query was: %s" % query
    
    def timeStamp(self):
        return strftime("%Y%m%d %H:%M:%S")
    


if __name__ == "__main__":
    user   = ''
    passwd = ''
    dbname = ''
    host   = ''
    
    db = DbInterface(user, passwd, dbname, host)
    print "\n"
    
    patch1 = db.get_patch(3)
    patch1.dump_info()
    print "\n"
    
    patch2 = db.get_patch()
    patch2.retreive_one("name", "Twins")
    patch2.dump_info()
    print "\n"
    
    patch3 = db.get_patch()
    patch3.retreive_one("name", "Kalith")
    patch3.dump_info()
    author1 = patch3.get_author()
    author1.dump_info()
    print "\n"
    
    author2 = db.get_author(5)
    author2.dump_info()
    print "\n"
    
    author3 = db.get_author()
    author3.retreive_one("name", "Az")
    author3.dump_info()
    print "\n"
    
    author4 = db.get_author()
    author4.set("name", "test1")
    author4.set("link", "blah blah blah")
    print "does author4 exist " + str(author4.exists())
    author4.create()
    print "does author4 exist " + str(author4.exists())
    author4.dump_info()
    print "\n"

    patch4 = db.get_patch()
    authid = author4.get("aid")
    print authid
    patch4.set("name", "testwerg")
    patch4.set("dlfile", "testwerg")
    patch4.set("aid", authid)
    print "does patch4 exist " + str(patch4.exists())
    patch4.create()
    print "does patch4 exist " + str(patch4.exists())
    patch4.dump_info()
    patch4.delete()
    print "does patch4 exist in db " + str(patch4.exists(True))
    author4.delete()
    print "does author4 exist in db " + str(author4.exists(True))
    print "\n"

    patch5 = db.get_patch(10)
    patch5.dump_info()
    plays = patch5.get("plays")
    patch5.set("plays", plays + 1)
    patch5.update()
    patch5.dump_info()




