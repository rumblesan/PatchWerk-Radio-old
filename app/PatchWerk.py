#!/usr/bin/env python

#Import Modules
import os
import sys
import signal
import ConfigParser
from DbInterface import DbInterface
from Radio import Radio
from optparse import OptionParser

def main():
    
    parser = OptionParser(usage='usage: %prog [-d] -c <configfile>')
    parser.add_option('-c', action='store', dest='configfile',
                      default='', help='Path to the config file', metavar='<configfile>')
    parser.add_option('-d', action='store_true', dest='debug',
                      default=False, help='Log all messages sent to PD')
    parser.add_option('-v', action='store_true', dest='verbose',
                      default=False, help='Print all log messages')
    (options, args) = parser.parse_args()
    
    
    if not os.path.isfile(options.configfile):
        print "File %s does not exist" % options.configfile
        sys.exit(1)
    
    config   = ConfigParser.SafeConfigParser()
    config.read(options.configfile)
    dbUser   = config.get('database', 'user')
    dbPasswd = config.get('database', 'password')
    dbHost   = config.get('database', 'host')
    dbName   = config.get('database', 'dbname')
    dbI      = DbInterface(dbUser, dbPasswd, dbName, dbHost)
    del(config)
    
    #create mixing/streaming patch
    radio = Radio(options, dbI)
    radio.pause(1)
    
    #register handler for SIGTERM
    signal.signal(signal.SIGTERM, radio.terminate)

    #register handler for SIGTERM
    signal.signal(signal.SIGINT, radio.terminate)
    
    #check that pure data is running fine
    if radio.check_pd():
        #register status with DB and turn DSP on
        radio.all_ok()
    else:
        sys.exit(1)
    
    #start streaming
    radio.streaming_setup()
    
    while True:
        #check to see if the control state is paused or not
        radio.control_check()

        #tell master PD to create the new patch
        radio.new_patch()
        
        if radio.loadError:
            #call function to deal with loading error
            radio.loading_error()
            
        else:
            #turn the DSP in the new patch on
            radio.activate_patch()
            
            #fade over to new patch
            radio.crossfade()
            
            #kill off old patch
            radio.kill_old_patch()
            
            #pause untill next patch needs to be loaded
            radio.play()

if __name__ == "__main__":
    main()
