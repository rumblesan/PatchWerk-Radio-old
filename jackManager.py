#!/usr/bin/env python

import sys
import re
from subprocess import Popen, PIPE
from time import sleep

class JackProgram():
    #used to keep track of the input and output ports of a program
    def __init__(self):
        self.inputs         = {}
        self.outputs        = {}


class JackManagement():
    #does all the interfacing with jack
    #will startup the jack daemon if required
    #interfacing is all done via the command line binaries
    def __init__(self, startup=True):
        
        #will start up the jack daemon if needed but doesn't have to
        if startup:
            #these command line args need to be added to the init arguments
            #also need to find out what they all do
            jackexe = "jackd"
            args = [jackexe]
            
            args.append("-P")
            args.append("70")
            
            args.append("-R")
            args.append("-dalsa")
            args.append("-dhw:0")
            args.append("-r44100")
            args.append("-p1024")
            args.append("-n2")
            
            self.jack = Popen(args, stdin=None, stderr=PIPE, stdout=PIPE, close_fds=(sys.platform != "win32"))
            
            # give jack a bit of time to come up
            sleep(1)
        else:
            self.jack = None
        
        #programNames holds a dictionary of the jackNames, keyed by the given program names
        self.programNames    = {}
        #jack programs holds a dictionary of JackProgram objects keyed by the jackNames
        self.jackPrograms = {}
        
        #regular expression for getting port numbers
        self.portNum  = re.compile('.*?([0-9]+)$')
        
    def __del__(self):
        #will call exit if object is deleted
        self.Exit()
        
    def Alive(self):
        #checks to see if the jack daemon process is alive
        if self.jack is not None:
            return bool(self.jack and self.jack.poll() != 0)
        else:
            return False
            
    def Exit(self):
        #will terminate the jack daemon if it is alive
        if self.Alive():
            self.jack.terminate()



    def _get_jack_data(self,extras=None):
        #get a list of the current jack connections
        args = ["jack_lsp"]
        #extras are used to add further command line arguments
        if extras != None:
            args.extend(extras)
        #rewrite this to use the python2.7 Popen helper methods
        getList = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        data, errors = getList.communicate()
        retVal = getList.wait()
        if retVal > 0:
            print errors
        #rstrip to remove the newline character at the end of the string
        return data.rstrip()
        
    def register_program(self, programName):
        #register a program with the jack manager
        #needs to be called after each new program has been started
        
        #check that the program isn't already registered
        if programName not in self.programNames.keys():
            jackData = self._get_jack_data()
            for info in jackData.splitlines():
                name, port = info.split(":")
                #check that the jackName is not already a registered program
                if name not in self.programNames.iteritems():
                    #create a new entry in the programNames dictionary
                    self.programNames[programName] = name
                    #create a new JackProgram object
                    self.jackPrograms[name] = JackProgram()
                    break
        #returns the jackName of the registered program
        return self.programNames[programName]

    def get_ports(self, programName):
        inportNumber  = 0
        outportNumber = 0
        #get a list of the input and output ports of the given program
        jackName = self.programNames[programName]
        
        #get the port properties data from jack
        jackData = self._get_jack_data(["-p"])
        #put all the data about single ports on one line
        jackData = re.sub(r'\n\tproperties: ',':',jackData)
        for info in jackData.splitlines():
            name, port, properties = info.split(":")
            if name == jackName:
                #the first element of the properties details whether the port
                #is an input or output
                inorout = properties.split(",").pop(0)
                
                #add ports to the JackProgram object dicts keyed on port number
                #note, we assign port numbers to avoid confusion
                if inorout == "input":
                    inportNumber += 1
                    self.jackPrograms[jackName].inputs[inportNumber] = port
                elif inorout == "output":
                    outportNumber += 1
                    self.jackPrograms[jackName].outputs[outportNumber] = port
        
        #return a tuple with number of input and output ports
        return (inportNumber, outportNumber)


    def connect_programs(self, sourceProgram, sourcePorts, sinkProgram, sinkPorts):
        #connect the specified port list of two programs together
        #ports are specified as list of port numbers, starting from 1
        
        #Notes: need to check that both lists are the same length
        
        #get jackNames for each program
        sourceJackName = self.programNames[sourceProgram]
        sinkJackName   = self.programNames[sinkProgram]
        
        #loop through the two port number lists
        for outNum, inNum in zip(sourcePorts, sinkPorts):
            outPort = self.jackPrograms[sourceJackName].inputs[outNum]
            inPort  = self.jackPrograms[sinkJackName].inputs[inNum]
            
            #create full port names
            sourceName = sourceJackName + ":" + outPort
            sinkName   = sinkJackName + ":" + inPort
            #pass data to jack_connect binary
            self._connect(sourceName, sinkName)

        
    def _connect(self, sourcePort, sinkPort):
        #interface with the jack_connect binary
        
        #create args list
        args = ["jack_connect"]
        args.append(sourcePort)
        args.append(sinkPort)
        
        #should rewrite this with the python 2.7 Popen lib helper functions
        connect = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        retVal = connect.wait()
        return 0
        
        
    def disconnect_program(self, programName):
        #disconnect all the ports for a given program
        
        jackName = self.programNames[programName]
        
        #gets connection data from jack_lsp binary
        jackData = self._get_jack_data(["-c"])
        #puts all the data for single ports on one line
        jackData = re.sub(r'\n   ',',',jackData)
        for info in jackData.splitlines():
            data = info.split(",")
            #get data for main program port
            progData = data.pop(0)
            name, port = progData.split(":")
            #if it's the program we want to disconnect then loop through
            #remaining port data and disconnect them all
            if name == jackName:
                for connection in data:
                    #pass data to jack_disconnect binary
                    self._disconnect(progData,connection)
                    
    def _disconnect(self, sourcePort, sinkPort):
        #interface with the jack_disconnect binary
        args = ["jack_disconnect"]
        args.append(sourcePort)
        args.append(sinkPort)
        
        #should rewrite this with the python 2.7 Popen lib helper functions
        disconnect = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        retVal = disconnect.wait()
        return retVal


def _test():
    #basic test case
    #creates a jackManager
    #starts jack daemon
    #registers system ports
    #gets port number
    #disconnects all system ports
    #deletes jackManager object
    jackManager = JackManagement(False)
    print jackManager.Alive()
    print jackManager.register_program("master")
    print jackManager.get_ports("master")
    print jackManager.disconnect_program("master")
    del(jackManager)

if __name__ == "__main__":
    _test()
