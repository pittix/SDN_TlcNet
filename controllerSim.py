#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import Controller
import os

class POXcontroller1( Controller):
	def start(self):
		self.pox='%s/pox/pox.py' %os.environ['HOME']
		self.cmd(self.pox, "lab3_1_controller &")

	def stop(self):
		self.cmd('kill %' +self.pox)

controllers = { 'poxcontroller1': POXcontroller1}



class myTopo(Topo):

	"Single switch connected to n hosts."
	def __init__(self, n=2, **opts):
		Topo.__init__(self, **opts)
		switch = self.addSwitch('s1')
		# Each host gets 50%/n of system CPU
		h1=self.addHost('h1', cpu=.5/n)
		h2=self.addHost('h2', cpu=.5/n)

		# 10 Mbps, 10ms delay, 0% loss, 1000 packet queue
		self.addLink('h1', switch, bw=10, delay='10ms', loss=0,max_queue_size=1000, use_htb=True)
		self.addLink('h2', switch, bw=10,delay='10ms', loss=0,max_queue_size=1000, use_htb=True)


def perfTest():
		"Create network and run simple performance test"
		topo = myTopo(n=2)
		net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=POXcontroller1)
		net.start()
		print "Dumping host connections"
		dumpNodeConnections(net.hosts)
		print "Testing network connectivity"
		net.pingAll()

		print "Testing bandwidth between h1 and h2"
		h1, h2 = net.get('h1', 'h2')
		net.iperf((h1, h2))
		net.stop()

if __name__ == '__main__':
		setLogLevel('info')
		perfTest()
