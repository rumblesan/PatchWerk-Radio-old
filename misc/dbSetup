#!/usr/bin/env python

import MySQLdb
from time import sleep
import sys

host = 'localhost'
user = 'root'
passwd = ''

newuser = ''
newpass = ''
newdb = ''

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
CREATE TABLE IF NOT EXISTS `radiocontrol` (
  `control` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  PRIMARY KEY (`control`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

INSERT INTO `radiocontrol` (`control`, `status`) VALUES
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
CREATE TABLE IF NOT EXISTS `patchplays` (
  `patchname` varchar(50) NOT NULL,
  `playnum` int(11) NOT NULL,
  PRIMARY KEY (`patchname`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
""")

queries.append("""
CREATE TABLE IF NOT EXISTS `patchinfo` (
  `patchname` varchar(50) NOT NULL,
  `author` varchar(50) NOT NULL,
  PRIMARY KEY (`patchname`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
""")

queries.append("""
CREATE TABLE IF NOT EXISTS `radioinfo` (
  `info` varchar(20) NOT NULL,
  `value` varchar(50) NOT NULL,
  PRIMARY KEY (`info`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

INSERT INTO `radioinfo` (`info`, `value`) VALUES
('status', 'down'),
('current', 'none'),
('previous', 'none');
""")

for query in queries:
    cursor = db.cursor()
    cursor.execute(query)
    cursor.close()


