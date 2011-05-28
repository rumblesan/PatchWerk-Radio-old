#!/usr/bin/env python

import MySQLdb
from time import sleep
import sys

dbenv = sys.argv[1]

host = 'localhost'
user = 'root'
passwd = ''

if dbenv = "master":
    newuser = 'patchwerk'
    newpass = ''
    newdb = 'radio'
else:
    newuser = 'testpatchwerk'
    newpass = ''
    newdb = 'testradio'

try:
    db = MySQLdb.connect(host, user, passwd)
except MySQLdb.Error, e:
    print "Error %d: %s" %(e.args[0], e.args[1])
    sys.exit(1)

print 'Connected'


queries = ["CREATE DATABASE IF NOT EXISTS %s" % newdb]

queries.append("""CREATE USER '%s'@'localhost' IDENTIFIED BY '%s'""" % (newuser, newpass))

queries.append("GRANT ALL PRIVILEGES ON  %s . * TO  '%s'@'localhost' WITH GRANT OPTION" % (newdb, newuser))

queries.append("USE %s" % newdb)

queries.append("""
CREATE TABLE IF NOT EXISTS `radio` (
  `info` varchar(20) NOT NULL,
  `value` varchar(50) NOT NULL,
  PRIMARY KEY (`info`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

INSERT INTO `radioinfo` (`info`, `value`) VALUES
('status', ''),
('current', ''),
('previous', ''),
('loading', 'on');
""")

queries.append("""
CREATE TABLE IF NOT EXISTS `logs` (
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `message` text NOT NULL,
  KEY `timestamp` (`timestamp`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
""")

queries.append("""
CREATE TABLE IF NOT EXISTS `patches` (
  `pid` int(11) NOT NULL AUTO_INCREMENT,
  `patchname` varchar(50) NOT NULL,
  `plays` bigint(20) NOT NULL,
  `aid` int(11) NOT NULL AUTO_INCREMENT,
  `dlfile` varchar(100) NOT NULL,
  PRIMARY KEY (`pid`),
  UNIQUE KEY `patchname` (`patchname`),
  KEY `author` (`author`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=33 ;
""")

queries.append("""
CREATE TABLE IF NOT EXISTS `authors` (
  `aid` int(11) NOT NULL AUTO_INCREMENT,
  `author` varchar(50) NOT NULL,
  `link` varchar(100) NOT NULL,
  PRIMARY KEY (`aid`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=9 ;
""")

queries.append("""
CREATE TABLE IF NOT EXISTS `users` (
  `uid` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(20) NOT NULL,
  `password` char(32) NOT NULL,
  PRIMARY KEY (`uid`),
  UNIQUE KEY `username` (`username`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=2 ;
""")

for query in queries:
    cursor = db.cursor()
    cursor.execute(query)
    cursor.close()


