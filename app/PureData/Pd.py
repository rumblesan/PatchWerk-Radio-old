#
#    This file is copyright Chris McCormick (PodSix Video Games), 2008
#
#    It is licensed under the terms of the LGPLv3
#

# import the monkey-patched subprocess which allows non-blocking reading on Windows
from monkeysubprocess import Popen, PIPE
from os import environ, read, getcwd
import sys
import signal
import asyncore
import asynchat
import socket
import select
import re
from time import sleep

import select
if hasattr(select, 'poll'):
    from asyncore import poll2 as poll
else:
    from asyncore import poll

cr = re.compile("[\r\n]+")

# monkey patch older versions to support maps in asynchat. Yuck.
if float(sys.version[:3]) < 2.6:
    def asynchat_monkey_init(self, conn=None, map=None):
        self.ac_in_buffer = ''
        self.ac_out_buffer = ''
        self.producer_fifo = asynchat.fifo()
        asyncore.dispatcher.__init__ (self, sock=conn, map=map)
    asynchat.async_chat.__init__ = asynchat_monkey_init

class PdException(Exception):
    pass


class PdComs(asynchat.async_chat):
    def __init__(self, parent, localaddr=("127.0.0.1", 30320), map=None):
        self._parent = parent
        self._cache = []
        self._success = False
        asynchat.async_chat.__init__(self, map=map)
        self._ibuffer = ""
        self.set_terminator(";\n")
        # address of Pd connection socket
        self._remote = ""
        # set up the server socket to do the accept() from Pd's socket
        self._serversocket = asyncore.dispatcher(map=map)
        self._serversocket.handle_accept = self.handle_accept_server
        self._serversocket.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serversocket.set_reuse_addr()
        self._serversocket.bind(localaddr)
        self._serversocket.listen(1)

    def handle_connect(self):
        self._success = True
        [self.Send(d) for d in self._cache]
    
    def handle_close(self):
        self.close()
    
    def handle_expt(self):
        data = 'PdSend: connection failed (win) or OOB data (linux)'
        self._parent.ComError(data)
        self.close()
        
    def handle_accept_server(self):
        accepted = self._serversocket.accept()
        if accepted:
            conn, addr = accepted
            self._remote = addr
            # close down and get rid of the server socket
            # as we don't want to accept any more incoming connections
            self._serversocket.close()
            del self._serversocket
            self.set_socket(conn)
        else:
            data = ("Dropped spurious PdReceive connect! socket:", self._socket, accepted)
            self._parent.ComError(data)
    
    def collect_incoming_data(self, data):
        self._ibuffer += data
    
    def found_terminator(self):
        data = self._ibuffer.split(" ")
        self._ibuffer = ""
        
        method = getattr(self._parent, 'Pd_' + data[0], None)
        if method:
            method(data[1:])
        else:
            self._parent.PdMessage(data)
            
    def Send(self, data):
        if self._success:
            asynchat.async_chat.push(self, " ".join([str(d) for d in data]) + ";\n")
        else:
            self._cache.append(data)
            
            

class Pd:
    """
        Start Pure Data in a subprocess.
        
        >>> from time import time, sleep
        >>> from os import path, getcwd
        >>> 
        >>> start = time()
        >>> # launching pd
        >>> pd = Pd(nogui=False)
        >>> pd.Send(["test message", 1, 2, 3])
        >>> 
        >>> def Pd_hello(self, message):
        ...     print "Pd called Pd_hello(%s)" % message
        ...
        >>> pd.Pd_hello = Pd_hello
        >>> 
        >>> sentexit = False
        >>> # running a bunch of stuff for up to 20 seconds
        >>> while time() - start < 20 and pd.Alive():
        ...     if time() - start > 0.5 and not sentexit:
        ...         pd.Send(["exit"])
        ...         sentexit = True
        ...     pd.Update()
        ...
        ...
        Pd called Pd_hello(['this', 'is', 'my', 'message', 'to', 'python'])
        untrapped message: ['this', 'is', 'another', 'message']
        untrapped stderr output: "connecting to port 30322"
        untrapped stderr output: "python-connected: 0"
        untrapped stderr output: "python-connected: 1"
        untrapped stderr output: "from-python: test message 1 2 3"
        untrapped stderr output: "closing audio..."
        untrapped stderr output: "pd_gui: pd process exited"
        untrapped stderr output: "closing MIDI..."...
        Pd died!
        >>> pd.Exit()
    """
    errorCallbacks = {}
    def __init__(self, port=30321, gui=True, open="python-interface-help.pd", cmd=None, path=["patches"], extra=None):
        """
        port - what port to connect to Pd on.
        nogui - boolean: whether to start Pd with or without a gui. Defaults to nogui=True
        open - string: full path to a .pd file to open on startup.
        cmd - message to send to Pd on startup.
        path - an array of paths to add to Pd startup path.
        extra - a string containing extra command line arguments to pass to Pd.
        """
        self.connectCallback = None
        
        if sys.platform == "win32":
            pdexe = "pd\\bin\\pd.exe"
        elif sys.platform == "linux2":
            pdexe = "pd"
        elif sys.platform == "darwin":
            pdexe = "./Pd.app/Contents/Resources/bin/pd"
        else:
            raise PdException("Unknown Pd executable location on your platform ('%s')." % sys.platform)
        args = [pdexe]
        
        args.append("-stderr")
        
        if not gui:
            args.append("-nogui")
        
        for p in path:
            args.append("-path")
            args.append(p)
        
        if extra:
            args += extra.split(" ")
        
        if open:
            args.append("-open")
            args.append(open)

        args.append("-send")
        args.append("startup port " + str(port))
        
        if cmd:
            args.append(cmd)
        
        self.argLine = " ".join(args)

        try:
            self.pd = Popen(args, stdin=None, stderr=PIPE, stdout=PIPE, close_fds=(sys.platform != "win32"))
        except OSError:
            raise PdException("Problem running `%s` from '%s'" % (pdexe, getcwd()))
        
        
        self.port    = port
        self._map    = {}
        self._pdComs = PdComs(self, localaddr=("127.0.0.1", port), map=self._map)
    
    #Internaly called functions
    def Dead(self):
        self.pd = None
        self.PdDied()
    
    def CheckStart(self, msg):
        if "_Start() called" in msg:
            self.PdStarted()
    
    #User callable functions
    def Update(self):
        poll(map=self._map)
        stdin = self.pd.recv()
        stderr = self.pd.recv_err()
        if stdin:
            [self.CheckStart(t) for t in cr.split(stdin) if t]
        if stderr:
            [self.Error(t) for t in cr.split(stderr) if t]
    
    def Send(self, msg):
        """
        Send an array of data to Pd.
        It will arrive at the [python-interface] object as a space delimited list.
        
        p.Send(["my", "test", "yay"])
        """
        self._pdComs.Send(msg)
    
    def Alive(self):
        """
        Check whether the Pd subprocess is still alive.
        """
        return bool(self.pd and self.pd.poll() != 0)
    
    def Exit(self):
        """
        Kill the Pd process right now.
        """
        if self.Alive():
            #self.close()
            if sys.platform == "win32":
                # Kill the process using pywin32
                import win32api
                win32api.TerminateProcess(int(self.pd._handle), -1)
            else:
                # kill the process using os.kill
                from os import kill
                kill(self.pd.pid, signal.SIGINT)
        if self.pd:
            self.pd.wait()
    
    #Functions to override
    def PdMessage(self, data):
        """
        Override this method to receive messages from Pd.
        """
        print "untrapped message:", data
    
    def Error(self, error):
        """
        Override this to catch anything sent by Pd to stderr (e.g. [print] objects).
        """
        errors = error.split(" ")
        method = getattr(self, 'Error_' + errors[0], None)
        if method:
            method(errors)
        elif error in self.errorCallbacks:
            self.errorCallbacks[error]()
        else:
            print 'untrapped stderr output: "' + error + '"'
    
    def PdStarted(self):
        """
        Override this to catch the definitive start of Pd.
        """
        print "Pd started!"
    
    def PdDied(self):
        """
        Override this to catch the Pd subprocess exiting.
        """
        print "Pd died!"
        
    def ComError(self, data):
        """
        Override this to catch errors during communication with PD.
        """
        print "Pd died!"
    
def _test():
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

if __name__ == "__main__":
    _test()
