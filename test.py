from time import time, sleep
from os import path, getcwd
from Pd import Pd

start = time()
# launching pd
pd = Pd(gui=True,open="python-interface-help.pd", cmd="startup port 30201")
pd.Send(["test message", 1, 2, 3])

def Pd_hello(self, message):
	print "Pd called Pd_hello(%s)" % message

def Pd_this(self, message):
	print "Pd called Pd_this(%s)" % message

pd.Pd_hello = Pd_hello
pd.Pd_this = Pd_this
pd.Send([" this is a further test"])


sentexit = False
# running a bunch of stuff for up to 20 seconds
while time() - start < 60 and pd.Alive():
	if time() - start > 20 and not sentexit:
		pd.Send(["exit"])
		sentexit = True
	pd.Update()

if pd.Alive():
	pd.Exit()

