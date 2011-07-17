#!/usr/bin/env python

import MySQLdb
from time import sleep
import sys

dbenv = sys.argv[1]

host = 'localhost'
user = ''
passwd = ''

if dbenv == "master":
    newuser = ''
    newpass = ''
    newdb = ''
else:
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
CREATE TABLE IF NOT EXISTS `authors` (
  `aid` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `link` varchar(100) NOT NULL,
  PRIMARY KEY (`aid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

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
  `name` varchar(50) NOT NULL,
  `plays` bigint(20) NOT NULL DEFAULT '0',
  `aid` int(11) NOT NULL,
  `dlfile` varchar(100) NOT NULL DEFAULT '',
  PRIMARY KEY (`pid`),
  UNIQUE KEY `name` (`name`),
  KEY `authors` (`aid`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;
""")


queries.append("""
CREATE TABLE IF NOT EXISTS `radio` (
  `id` int(11) NOT NULL,
  `status` varchar(50) NOT NULL,
  `loading` varchar(50) NOT NULL,
  `playing` varchar(50) NOT NULL,
  `previous` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

INSERT INTO `radio` (`id`, `status`, `loading`, `playing`, `previous`) VALUES
(1, '', 'on', '', '');
""")


queries.append("""
CREATE TABLE IF NOT EXISTS `users` (
  `uid` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL,
  `password` char(32) NOT NULL,
  PRIMARY KEY (`uid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=2 ;
""")

for query in queries:
    print query
    cursor = db.cursor()
    cursor.execute(query)
    cursor.close()


