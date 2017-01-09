# Copyright 2011 James McCauley
# Copyright 2008 (C) Nicira, Inc.
#
# This file is part of POX.
#
#
## Modifications by Farzaneh Pakzad
## Date: 10/3/2015
## Summary of modifications:
## The key difference of this version to the original version is that
## instead of sending a Packet_Out message with an LLDP packet for each port on each switch
## we are only sending a single Packet_Out message, together with instructions to the
## switch to send it out on each port. To provide a unique source port identifier, the
## source MAC address is rewritten by the switch to match the MAC address of the egress port.
##
#
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX. If not, see <http://www.gnu.org/licenses/>.

# This file is based on the discovery component in NOX, though it has
# been substantially rewritten.

"""
This module discovers the connectivity between OpenFlow switches by sending
out LLDP packets. To be notified of this information, listen to LinkEvents
on core.Discovery.
It's possible that some of this should be abstracted out into a generic
Discovery module, or a Discovery superclass.
"""

from pox.lib.revent import *
from pox.lib.recoco import Timer

#from pox.lib.packet.ethernet import LLDP_MULTICAST, NDP_MULTICAST
#from pox.lib.packet.ethernet import ethernet
#from pox.lib.packet.lldp import lldp, chassis_id, port_id, end_tlv
#from pox.lib.packet.lldp import ttl, system_description

import pox.lib.packet as pkt
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str, str_to_bool
from pox.core import core

import struct
import array
import socket
import time
import os
import copy
from collections import *

LLDP_TTL = 120 # currently ignored
LLDP_SEND_CYCLE = 0.3
TIMEOUT_CHECK_PERIOD = 5.0
LINK_TIMEOUT = 10.0
CPU_TIME_INTERVAL = 0.2

log = core.getLogger()

class LLDPSender (object):
  """
Cycles through a list of packets, sending them such that it completes the
entire list every LLDP_SEND_CYCLE.
"""
  SendItem = namedtuple("LLDPSenderItem",
                      ('dpid','port_num','packet'))

  #NOTE: This class keeps the packets to send in a flat list, which makes
  # adding/removing them on switch join/leave or (especially) port
  # status changes relatively expensive. This could easily be improved.

  def __init__ (self):
    self._packets = []
    #change
    self._ports = []
    self._timer = None

  def add_switch (self, dpid, ports):
    """ Ports are (port_num, port_addr) """

    self._ports = ports
    self._packets = [p for p in self._packets if p.dpid != dpid]

    ###new changes
    "all packet get the same port_num and port addr when created"
    port_num = 0
    port_addr = '00:00:00:00:00:00'
    self.add_port(dpid, port_num, port_addr)
    self._setTimer()

  def del_switch (self, dpid):
    self._packets = [p for p in self._packets if p.dpid != dpid]
    self._setTimer()

  def del_port (self, dpid, port_num):
    self._packets = [p for p in self._packets
                     if p.dpid != dpid or p.port_num != port_num]
    self._setTimer()

  def add_port (self, dpid, port_num, port_addr):
    self.del_port(dpid, port_num)
    self._packets.append(LLDPSender.SendItem(dpid, port_num,
         self.create_discovery_packet(dpid, port_num, port_addr)))
    self._setTimer()

  def _setTimer (self):
    if self._timer: self._timer.cancel()
    self._timer = None
    if len(self._packets) != 0:
      self._timer = Timer(LLDP_SEND_CYCLE / len(self._packets),
                          self._timerHandler, recurring=True)

  def _timerHandler (self):
    """
    Called by a timer to actually send packet.
    Picks the first packet off the queue, sends it, and puts it     back on the
    end of the queue.
    """
    if len(self._packets) != 0:
      item = self._packets.pop(0)
      self._packets.append(item)
      core.openflow.sendToDPID(item.dpid, item.packet)


  def create_discovery_packet (self, dpid, port_num, port_addr):
    """ Create LLDP packet """

    chassis_id = pkt.chassis_id(subtype=pkt.chassis_id.SUB_LOCAL)
    chassis_id.id = bytes('dpid:' + hex(long(dpid))[2:-1])
    # Maybe this should be a MAC.  But a MAC of what?  Local port, maybe?

    port_id = pkt.port_id(subtype=pkt.port_id.SUB_PORT, id=str(port_num))

    ttl = pkt.ttl(ttl = LLDP_TTL)

    sysdesc = pkt.system_description()
    sysdesc.payload = bytes('dpid:' + hex(long(dpid))[2:-1])

    discovery_packet = pkt.lldp()
    discovery_packet.tlvs.append(chassis_id)
    discovery_packet.tlvs.append(port_id)
    discovery_packet.tlvs.append(ttl)
    discovery_packet.tlvs.append(sysdesc)
    discovery_packet.tlvs.append(pkt.end_tlv())
    #discovery_packet = pkt.ethernet()
    eth = pkt.ethernet(type=pkt.ethernet.LLDP_TYPE)
    eth.src = port_addr
    eth.dst = pkt.ETHERNET.NDP_MULTICAST
    eth.payload = discovery_packet

    for item in self._ports:
      if item[0] > of.OFPP_MAX:
        self._ports.remove(item)
    #print "ports after remove = ", self._ports

    actions1 = []
    for port_num, port_addr in self._ports:
        actions1.append(of.ofp_action_dl_addr.set_src(port_addr))
        actions1.append(of.ofp_action_output(port = port_num))

    po = of.ofp_packet_out()
    po.actions = actions1
    po.data = eth.pack()
    return po.pack()


class LinkEvent (Event):
  def __init__ (self, add, link):
    Event.__init__(self)
    self.link = link
    self.added = add
    self.removed = not add

  def portForDPID (self, dpid):
    if self.link.dpid1 == dpid:
      return self.link.port1
    if self.link.dpid2 == dpid:
      return self.link.port2
    return None


class Discovery (EventMixin):
  """
Component that attempts to discover topology.
Works by sending out LLDP packets
discovery application for topology inference
"""

  _eventMixin_events = set([
    LinkEvent,
  ])
  _dpidports
  _core_name = "openflow_discovery" # we want to be core.openflow_discovery

  Link = namedtuple("Link",("dpid1","port1","dpid2","port2"))

  def __init__ (self, install_flow = True, explicit_drop = True):
    self.explicit_drop = explicit_drop
    self.install_flow = install_flow

    self._dps = set()
    self._dpidports = dict()
    self.adjacency = {} # From Link to time.time() stamp
    self._sender = LLDPSender()
    Timer(TIMEOUT_CHECK_PERIOD, self._expireLinks, recurring=True)

    if core.hasComponent("openflow"):
      self.listenTo(core.openflow)
    else:
      # We'll wait for openflow to come up
      self.listenTo(core)

  def _handle_ComponentRegistered (self, event):
    if event.name == "openflow":
      self.listenTo(core.openflow)
      return EventRemove # We don't need this listener anymore

  def _handle_ConnectionUp (self, event):
    """ On datapath join, create a new LLDP packet per port """
    assert event.dpid not in self._dps

    self._dps.add(event.dpid)
    ports = [(p.port_no, str(p.hw_addr)) for p in event.ofp.ports]
    self._dpidports[event.dpid]= ports
    self._sender.add_switch(event.dpid, ports)

  def _handle_ConnectionDown (self, event):
    """ On datapath leave, delete all associated links """
    assert event.dpid in self._dps

    self._dps.remove(event.dpid)
    self._sender.del_switch(event.dpid)

    deleteme = []
    for link in self.adjacency:
      if link.dpid1 == event.dpid or link.dpid2 == event.dpid:
        deleteme.append(link)

    self._deleteLinks(deleteme)

  def _handle_PortStatus (self, event):
    '''
Update the list of LLDP packets if ports are added/removed
Add to the list of LLDP packets if a port is added.
Delete from the list of LLDP packets if a port is removed.
'''
    # Only process 'sane' ports
    if event.port <= of.OFPP_MAX:
      if event.added:
        self._sender.add_port(event.dpid, event.port, event.ofp.desc.hw_addr)
      elif event.deleted:
        self._sender.del_port(event.dpid, event.port)

  def _expireLinks (self):
    '''
Called periodially by a timer to expire links that haven't been
refreshed recently.
'''
    curtime = time.time()

    deleteme = []
    for link,timestamp in self.adjacency.iteritems():
      if curtime - timestamp > LINK_TIMEOUT:
        deleteme.append(link)
        log.info('link timeout: %s.%i -> %s.%i' %
                 (dpid_to_str(link.dpid1), link.port1,
                  dpid_to_str(link.dpid2), link.port2))

    if deleteme:
      self._deleteLinks(deleteme)

  def _handle_PacketIn (self, event):
    """ Handle incoming lldp packets. Use to maintain link state """


    packet = event.parse()

    if packet.effective_ethertype != pkt.ethernet.LLDP_TYPE: return
    if packet.dst != pkt.ETHERNET.NDP_MULTICAST: return


    if not packet.next:
      log.error("lldp packet could not be parsed")
      return


    if self.explicit_drop:
      if event.ofp.buffer_id != -1:
        log.debug("Dropping LLDP packet %i", event.ofp.buffer_id)
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        event.connection.send(msg)


    lldph = packet.find(pkt.lldp)

    if lldph is None or not lldph.parsed:
      log.error("LLDP packet could not be parsed")
      return EventHalt

    if len(lldph.tlvs) < 3 or \
      (lldph.tlvs[0].tlv_type != pkt.lldp.CHASSIS_ID_TLV) or\
      (lldph.tlvs[1].tlv_type != pkt.lldp.PORT_ID_TLV) or\
      (lldph.tlvs[2].tlv_type != pkt.lldp.TTL_TLV):
      log.error("lldp_input_handler invalid lldp packet")
      return


    def lookforDPID_Port():
      for key,value in self._dpidports.iteritems():
        for item in value:
          if item[1] == packet.src.toStr():
              DPID = key
              Port = item[0]
              return DPID, Port

    originatorDPID, originatorPort = lookforDPID_Port()
    #print "(originatorDPID, originatorPort) =", originatorDPID, originatorPort

    if originatorDPID == None:
      log.warning("Couldn't find a DPID in the LLDP packet")
      return

    # if chassid is from a switch we're not connected to, ignore
    if originatorDPID not in self._dps:
      log.info('Received LLDP packet from unconnected switch')
      return

    if originatorPort is None:
      log.warning("Thought we found a DPID, but port number didn't " +
                  "make sense")
      return

    if (event.dpid, event.port) == (originatorDPID, originatorPort):
      log.error('Loop detected; received our own LLDP event')
      return


    link = Discovery.Link(originatorDPID, originatorPort, event.dpid,
                          event.port)

    if link not in self.adjacency:
      self.adjacency[link] = time.time()
      log.info('link detected: %s.%i -> %s.%i' %
              (dpid_to_str(link.dpid1), link.port1,
                dpid_to_str(link.dpid2), link.port2))

      self.raiseEventNoErrors(LinkEvent, True, link)
    else:
      # Just update timestamp
      self.adjacency[link] = time.time()

    return EventHalt # Probably nobody else needs this event


  def _deleteLinks (self, links):
    for link in links:
      del self.adjacency[link]
      self.raiseEvent(LinkEvent, False, link)


  def isSwitchOnlyPort (self, dpid, port):
    """ Returns True if (dpid, port) designates a port that has any
neighbor switches"""
    for link in self.adjacency:
      if link.dpid1 == dpid and link.port1 == port:
        return True
      if link.dpid2 == dpid and link.port2 == port:
        return True
    return False


def launch (explicit_drop = False, install_flow = True):
  explicit_drop = str(explicit_drop).lower() == "true"
  install_flow = str(install_flow).lower() == "true"
  core.registerNew(Discovery, explicit_drop=explicit_drop,
install_flow=install_flow)
