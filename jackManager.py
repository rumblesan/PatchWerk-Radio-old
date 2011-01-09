#!/usr/bin/env python


from subprocess import Popen, PIPE
import sys
from time import sleep
import re

class ProgramPorts():
    def __init__(self):
        self.inputs  = {}
        self.outputs = {}



class JackManagement():
    
    def __init__(self):
        
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
        
        self.programs    = {}
        self.connections = {}

        self.portNum  = re.compile('.*?([0-9]+)$')
        
    def __del__(self):
        self.Exit()
        
    def Alive(self):
        return bool(self.jack and self.jack.poll() != 0)
        
    def Exit(self):
        if self.Alive():
            self.jack.terminate()



    def get_connections(self,extras=None):
        #get a list of the current jack connections
        args = ["jack_lsp"]
        if extras != None:
            args.extend(extras)
        getList = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        connections, errors = getList.communicate()
        retVal = getList.wait()
        if retVal > 0:
            print errors
        return connections.rstrip()
        
    def register_program(self, programName):
        
        if programName not in self.programs.keys():
            connections = self.get_connections()
            for info in connections.splitlines():
                name, port = info.split(":")
                if name not in self.programs.iteritems():
                    self.programs[programName] = name
                    break
        
        return self.programs[programName]

    def get_ports(self, programName):
        jackName = self.programs[programName]
        self.connections[jackName] = ProgramPorts()

        connections = self.get_connections(["-p"])
        connections = re.sub(r'\n\tproperties: ',':',connections)
        for info in connections.splitlines():
            name, port, properties = info.split(":")
            if name == jackName:
                inorout = properties.split(",").pop(0)
                portNumber = self.portNum.search(port).group(1)
                if inorout == "input":
                    self.connections[jackName].inputs[portNumber] = port
                elif inorout == "output":
                    self.connections[jackName].outputs[portNumber] = port

        inNum  = len(self.connections[jackName].inputs)
        outNum = len(self.connections[jackName].outputs)
        return (inNum, outNum)

    def connect_programs(self, source, sourcePorts, sink, sinkPorts):
        
        sourceProgram = self.programs[source]
        sinkProgram   = self.programs[sink]

        for outNum, inNum in zip(sourcePorts, sinkPorts):
            outPort = self.connections[sourceProgram].inputs[outNum]
            inPort  = self.connections[sinkProgram].inputs[inNum]

        
    def connect_ports(self, sourceProgram, sourcePort, sinkProgram, sinkPort):
        
        args = ["jack_connect"]
        args.append(sourceProgram + ":" + sourcePort)
        args.append(sinkProgram + ":" + sinkPort)

        connect = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        retVal = connect.wait()
        return 0
        
        
    def disconnect_program(self, program):
        args = ["jack_disconnect"]
        args.append(sourceProgram + ":" + sourcePort)
        args.append(sinkProgram + ":" + sinkPort)

        connect = Popen(args, stdin=None, stdout=PIPE, stderr=PIPE)
        retVal = connect.wait()
        return 0


def _test():
    jackManager = JackManagement()
    print jackManager.Alive()
    print jackManager.register_program("master")
    print jackManager.get_ports("master")
    del(jackManager)

if __name__ == "__main__":
    _test()
