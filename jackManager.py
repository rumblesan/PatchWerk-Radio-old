#!/usr/bin/env python


from subprocess import Popen, PIPE
import sys
from time import sleep
import re

class JackProgram():
    def __init__(self):
        self.inputs         = {}
        self.outputs        = {}


class JackManagement():
    
    def __init__(self, startup=True):
        
        if startup:
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
        else: self.jack = None

        self.programNames    = {}
        self.jackPrograms = {}

        self.portNum  = re.compile('.*?([0-9]+)$')
        
    def __del__(self):
        self.Exit()
        
    def Alive(self):
        return bool(self.jack and self.jack.poll() != 0)
        
    def Exit(self):
        if self.Alive():
            self.jack.terminate()



    def get_jack_data(self,extras=None):
        #get a list of the current jack connections
        args = ["jack_lsp"]
        if extras != None:
            args.extend(extras)
        getList = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        data, errors = getList.communicate()
        retVal = getList.wait()
        if retVal > 0:
            print errors
        return data.rstrip()
        
    def register_program(self, programName):
        
        if programName not in self.programNames.keys():
            jackData = self.get_jack_data()
            for info in jackData.splitlines():
                name, port = info.split(":")
                if name not in self.programNames.iteritems():
                    self.programNames[programName] = name
                    self.jackPrograms[name] = JackProgram()
                    break
        
        return self.programNames[programName]

    def get_ports(self, programName):
        jackName = self.programNames[programName]

        jackData = self.get_jack_data(["-p"])
        jackData = re.sub(r'\n\tproperties: ',':',jackData)
        for info in jackData.splitlines():
            name, port, properties = info.split(":")
            if name == jackName:
                inorout = properties.split(",").pop(0)
                portNumber = self.portNum.search(port).group(1)
                if inorout == "input":
                    self.jackPrograms[jackName].inputs[portNumber] = port
                elif inorout == "output":
                    self.jackPrograms[jackName].outputs[portNumber] = port

        inNum  = len(self.jackPrograms[jackName].inputs)
        outNum = len(self.jackPrograms[jackName].outputs)
        return (inNum, outNum)


    def connect_programs(self, source, sourcePorts, sink, sinkPorts):
        
        sourceProgram = self.programNames[source]
        sinkProgram   = self.programNames[sink]

        for outNum, inNum in zip(sourcePorts, sinkPorts):
            outPort = self.jackPrograms[sourceProgram].inputs[outNum]
            inPort  = self.jackPrograms[sinkProgram].inputs[inNum]

        
    def connect_ports(self, sourceProgram, sourcePort, sinkProgram, sinkPort):
        
        args = ["jack_connect"]
        args.append(sourceProgram + ":" + sourcePort)
        args.append(sinkProgram + ":" + sinkPort)

        connect = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        retVal = connect.wait()
        return 0
        
        
    def disconnect_program(self, programName):
        jackName = self.programNames[programName]
        jackData = self.get_jack_data(["-c"])
        jackData = re.sub(r'\n   ',',',jackData)
        for info in jackData.splitlines():
            data = info.split(",")
            progData = data.pop(0)
            name, port = progData.split(":")
            if name == jackName:
                for connection in data:
                    retval = self._disconnect(progData,connection)
                    
    def _disconnect(self, port1, port2):
        args = ["jack_disconnect"]
        args.append(port1)
        args.append(port2)

        disconnect = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        retVal = disconnect.wait()
        return retVal


def _test():
    jackManager = JackManagement(False)
    print jackManager.Alive()
    print jackManager.register_program("master")
    print jackManager.get_ports("master")
    print jackManager.disconnect_program("master")
    del(jackManager)

if __name__ == "__main__":
    _test()
