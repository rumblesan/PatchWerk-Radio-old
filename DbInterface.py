#!/usr/bin/env python

#import modules
import MySQLdb
import MySQLdb.cursors
import sys

class DbInterface():

    def __init__(self, user, passwd, db, host="localhost"):
        try:
            self.db = MySQLdb.connect(host=host,
                                      user=user,
                                      passwd=passwd,
                                      db=db,
                                      cursorclass=MySQLdb.cursors.DictCursor)
        except MySQLdb.Error, e:
            print "Error %d: %s" %(e.args[0], e.args[1])
            sys.exit(1)
    
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
    
    def get(self, key):
        return self.data[key]
    
    def set(self, key, value):
        if key in self.data:
            self.data[key] = value
    
    def exists(self):
        if self.data[self.key] != '':
            return false
        else:
            return true
    
    def dump_info(self):
        for col, value in self.data.iteritems():
            print "%s: %s" % (col.ljust(15), value)
    
    def retreive(self, value):
        sql = """SELECT *
                 FROM `%s`
                 WHERE `%s` = "%s"
              """ % (self.table, self.key, value)
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        if row != None:
            for col, value in row.iteritems():
                self.data[col] = value
    
    def retreive_one(self, key, value)
        sql = """SELECT *
                 FROM `%s`
                 WHERE `%s` = "%s"
              """ % (self.table, key, value)
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        if row != None:
            for col, value in row.iteritems():
                self.data[col] = value
    
    def update(self):
        colvals = []
        keyval = self.data[self.key]
        for col, value in self.data.iteritems():
            colvals.append(""" `%s`. = '%s' """ % (col, value))
        args = ", ".join(colvals)
        sql = """UPDATE `%s` SET %s WHERE `%s` = %i""" % (self.table, args, self.key, keyval)
        self.cursor.execute(sql)
    
    def create(self):
        cols = []
        vals = []
        keyval = self.data[self.key]
        for col, value in self.data.iteritems():
            cols.append("""`%s`""" % col)
            vals.append("""`%s`""" % value)
        colargs = ", ".join(cols)
        valargs = ", ".join(vals)
        sql = """INSERT INTO `%s` (%s) VALUES (`%s`)""" % (self.table, colargs, valargs)
        self.cursor.execute(sql)
    

class Patch(Model):

    def __init__(self, dbI, pid=''):
        Model.__init__(self, "pid", "patches", dbI)
        self.data['pid']       = ''
        self.data['patchname'] = ''
        self.data['plays']     = ''
        self.data['aid']       = ''
        self.data['dlfile']    = ''
        if (pid != ''):
            self.retreive(pid)
    
    def get_author(self):
        if self.data['aid'] != '':
            author = self.dbI.get_author(self.data['pid'])
            return author
    

class Author(Model):

    def __init__(self, cursor, pid=''):
        Model.__init__(self, "aid", "authors", dbI)
        self.data['aid']    = ''
        self.data['author'] = ''
        self.data['link']   = ''
        if (aid != ''):
            self.retreive(aid)
    
    def get_patches(self):
        if self.data['aid'] != '':
            author = self.dbI.get_author(self.data['pid'])
            return author
    

class Logger():
    #class to handle logging. prepends timestamp to data then prints it out
    
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
                """ % (self.logtable, message)
        self.cursor.execute(query)
    
    def timeStamp(self):
        return strftime("%Y%m%d %H:%M:%S")
    

class RadioInfo(Model):

    def __init__(self, cursor, id=''):
        Model.__init__(self, "id", "radio", dbI)
        self.data['id']       = ''
        self.data['status']   = ''
        self.data['loading']  = ''
        self.data['current']  = ''
        self.data['previous'] = ''
        if (id != ''):
            self.retreive(id)
    


if __name__ == "__main__":
    user   = ''
    passwd = ''
    dbname = ''
    host   = ''
    
    db = DBInterface(user, passwd, dbname, host)
    print "\n"
    
    patch1 = db.get_patch(3)
    patch1.dump_info()
    print "\n"
    
    patch2 = db.get_patch()
    patch2.retreive_one("Twins")
    patch2.dump_info()
    print "\n"
    
    patch3 = db.get_patch()
    patch3.retreive_one("Kalith")
    patch3.dump_info()
    author1 = patch3.get_author()
    author1.dump_info()
    print "\n"
    
    author2 = db.get_author(5)
    author2.dump_info()
    print "\n"
    
    author3 = db.get_author()
    author3.retreive_one("Az")
    author3.dump_info()
    print "\n"
    