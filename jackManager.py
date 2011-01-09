#!/usr/bin/env python


from subprocess import Popen, PIPE
import sys
from time import sleep


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

        self.programs       = {}

    def __del__(self):
        self.Exit()

    def Alive(self):
        return bool(self.jack and self.jack.poll() != 0)

    def Exit(self):
        if self.Alive():
            self.jack.terinate()

    def get_connections(self):
        #get a list of the current jack connections
        getList = Popen("jack_lsp", stdin=None, stdout=PIPE, stderr=PIPE)
        connections, errors = getList.communicate()
        retVal = getList.wait()
        if retVal > 0:
            print errors
        return connections

    def register_program(self, program):
        connections = jack.get_connections
        for info in connections:
            jackName, port = info.split(":")
            if jackName not in self.programs.keys():
        #differences between new list and old list
        #store jack name for program with key of given name
        #self.programs[programName] = jackName
        
    def connect_programs(self, source, sink):
        pass
        #source = self.programs[sourceProgram]
        #sink   = self.programs[sinkProgram]
        #jack.connect(source, sink)
        
    def disconnect_program(self, program):
        pass
        #jackname = self.programs[programName]
        #jack.disconnect(jackName)
        #del self.programs[programName]

def _test():
    jackManager = JackManagement()
    print jackManager.Alive()
    print jackManager.get_connections()
    del(jackManager)

if __name__ == "__main__":
    _test()
