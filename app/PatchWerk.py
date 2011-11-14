#!/usr/bin/env python

#Import Modules
import os
import sys
import signal
import ConfigParser
from DbInterface import DbInterface
from Radio import Radio
from optparse import OptionParser

import daemon
from daemon import pidlockfile

def PatchWerk(config, options):

    dbUser   = config.get('database', 'user')
    dbPasswd = config.get('database', 'password')
    dbHost   = config.get('database', 'host')
    dbName   = config.get('database', 'dbname')
    dbI      = DbInterface(dbUser, dbPasswd, dbName, dbHost)

    log = Logger(dbI, config.verbose)

    #create mixing/streaming patch
    radio = Radio(config, dbI)
    radio.pause(1)
    
    #register handler for SIGTERM
    signal.signal(signal.SIGTERM, radio.terminate)

    #register handler for SIGINT
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

def run_daemon(config, options):

    context = daemon.DaemonContext()

    context.working_directory = config.get('daemon', 'workingDir')

    pidpath = config.get('daemon', 'pidpath')
    pidfile = pidlockfile.PIDLockFile(pidpath)
    context.pidfile = pidfile
    context.umask = 0o666

    with context:
        PatchWerk(config, options)

def main():

    parser = OptionParser(usage='usage: %prog [-d] [-v] [-f] -c <configfile>')
    parser.add_option('-c', '--config', action='store', dest='configfile',
                      default='', help='Path to the config file', metavar='<configfile>')
    parser.add_option('-d', '--debug', action='store_true', dest='debug',
                      default=False, help='Log all messages sent to PD')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                      default=False, help='Print all log messages')
    parser.add_option('-f', '--foreground', action='store_true', dest='foreground',
                      default=False, help='Print all log messages')
    (options, args) = parser.parse_args()
    
    mandatories = ['configfile']
    for m in mandatories:
        if not opts.__dict__[m]:
            print "Mandatory option missing\n"
            parser.print_help()
            exit(-1)
    
    if opts.foreground == False and opts.verbose == True:
        opts.verbose = False
        print "Not running in foreground so switching verbose off"
    
    config = ConfigParser.SafeConfigParser()
    config.read(options.configfile)
    
    
    if opts.foreground == False:
        PatchWerk(config, options)
    else:
        run_daemon(config, options)


if __name__ == "__main__":
    main()
