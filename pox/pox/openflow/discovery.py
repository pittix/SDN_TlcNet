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
# Copyright 2011-2013 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file is loosely based on the discovery component in NOX.

"""
This module discovers the connectivity between OpenFlow switches by sending
out LLDP packets. To be notified of this information, listen to LinkEvents
on core.openflow_discovery.
It's possible that some of this should be abstracted out into a generic
Discovery module, or a Discovery superclass.
"""

from pox.lib.revent import *
from pox.lib.recoco import Timer
from pox.lib.util import dpid_to_str, str_to_bool
from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt

import struct
import time
from collections import namedtuple
from random import shuffle, random


log = core.getLogger()


class LLDPSender (object):
  """
  Sends out discovery packets
  """

  SendItem = namedtuple("LLDPSenderItem", ('dpid','port_num','packet'))

  #NOTE: This class keeps the packets to send in a flat list, which makes
  #      adding/removing them on switch join/leave or (especially) port
  #      status changes relatively expensive. Could easily be improved.

  # Maximum times to run the timer per second
  _sends_per_sec = 15

  def __init__ (self, send_cycle_time, ttl = 120):
    """
    Initialize an LLDP packet sender
    send_cycle_time is the time (in seconds) that this sender will take to
      send every discovery packet.  Thus, it should be the link timeout
      interval at most.
    ttl is the time (in seconds) for which a receiving LLDP agent should
      consider the rest of the data to be valid.  We don't use this, but
      other LLDP agents might.  Can't be 0 (this means revoke).
    """
    # Packets remaining to be sent in this cycle
    self._this_cycle = []

    # Packets we've already sent in this cycle
    self._next_cycle = []

    # Packets to send in a batch
    self._send_chunk_size = 1

    self._timer = None
    self._ttl = ttl
    self._send_cycle_time = send_cycle_time
    core.listen_to_dependencies(self)

  def _handle_openflow_PortStatus (self, event):
    """
    Track changes to switch ports
    """
    if event.added:
      self.add_port(event.dpid, event.port, event.ofp.desc.hw_addr)
    elif event.deleted:
      self.del_port(event.dpid, event.port)

  def _handle_openflow_ConnectionUp (self, event):
    self.del_switch(event.dpid, set_timer = False)

    ports = [(p.port_no, p.hw_addr) for p in event.ofp.ports]

    for port_num, port_addr in ports:
      self.add_port(event.dpid, port_num, port_addr, set_timer = False)

    self._set_timer()

  def _handle_openflow_ConnectionDown (self, event):
    self.del_switch(event.dpid)

  def del_switch (self, dpid, set_timer = True):
    self._this_cycle = [p for p in self._this_cycle if p.dpid != dpid]
    self._next_cycle = [p for p in self._next_cycle if p.dpid != dpid]
    if set_timer: self._set_timer()

  def del_port (self, dpid, port_num, set_timer = True):
    if port_num > of.OFPP_MAX: return
    self._this_cycle = [p for p in self._this_cycle
                        if p.dpid != dpid or p.port_num != port_num]
    self._next_cycle = [p for p in self._next_cycle
                        if p.dpid != dpid or p.port_num != port_num]
    if set_timer: self._set_timer()

  def add_port (self, dpid, port_num, port_addr, set_timer = True):
    if port_num > of.OFPP_MAX: return
    self.del_port(dpid, port_num, set_timer = False)
    self._next_cycle.append(LLDPSender.SendItem(dpid, port_num,
          self.create_discovery_packet(dpid, port_num, port_addr)))
    if set_timer: self._set_timer()

  def _set_timer (self):
    if self._timer: self._timer.cancel()
    self._timer = None
    num_packets = len(self._this_cycle) + len(self._next_cycle)

    if num_packets == 0: return

    self._send_chunk_size = 1 # One at a time
    interval = self._send_cycle_time / float(num_packets)
    if interval < 1.0 / self._sends_per_sec:
      # Would require too many sends per sec -- send more than one at once
      interval = 1.0 / self._sends_per_sec
      chunk = float(num_packets) / self._send_cycle_time / self._sends_per_sec
      self._send_chunk_size = chunk

    self._timer = Timer(interval,
                        self._timer_handler, recurring=True)

  def _timer_handler (self):
    """
    Called by a timer to actually send packets.
    Picks the first packet off this cycle's list, sends it, and then puts
    it on the next-cycle list.  When this cycle's list is empty, starts
    the next cycle.
    """
    num = int(self._send_chunk_size)
    fpart = self._send_chunk_size - num
    if random() < fpart: num += 1

    for _ in range(num):
      if len(self._this_cycle) == 0:
        self._this_cycle = self._next_cycle
        self._next_cycle = []
        #shuffle(self._this_cycle)
      item = self._this_cycle.pop(0)
      self._next_cycle.append(item)
      core.openflow.sendToDPID(item.dpid, item.packet)

  def create_discovery_packet (self, dpid, port_num, port_addr):
    """
    Build discovery packet
    """

    chassis_id = pkt.chassis_id(subtype=pkt.chassis_id.SUB_LOCAL)
    chassis_id.id = bytes('dpid:' + hex(long(dpid))[2:-1])
    # Maybe this should be a MAC.  But a MAC of what?  Local port, maybe?

    port_id = pkt.port_id(subtype=pkt.port_id.SUB_PORT, id=str(port_num))

    ttl = pkt.ttl(ttl = self._ttl)

    sysdesc = pkt.system_description()
    sysdesc.payload = bytes('dpid:' + hex(long(dpid))[2:-1])

    discovery_packet = pkt.lldp()
    discovery_packet.tlvs.append(chassis_id)
    discovery_packet.tlvs.append(port_id)
    discovery_packet.tlvs.append(ttl)
    discovery_packet.tlvs.append(sysdesc)
    discovery_packet.tlvs.append(pkt.end_tlv())

    eth = pkt.ethernet(type=pkt.ethernet.LLDP_TYPE)
    eth.src = port_addr
    eth.dst = pkt.ETHERNET.NDP_MULTICAST
    eth.payload = discovery_packet

    po = of.ofp_packet_out(action = of.ofp_action_output(port=port_num))
    po.data = eth.pack()
    return po.pack()


class LinkEvent (Event):
  """
  Link up/down event
  """
  def __init__ (self, add, link):
    Event.__init__(self)
    self.link = link
    self.added = add
    self.removed = not add

  def port_for_dpid (self, dpid):
    if self.link.dpid1 == dpid:
      return self.link.port1
    if self.link.dpid2 == dpid:
      return self.link.port2
    return None


class Link (namedtuple("LinkBase",("dpid1","port1","dpid2","port2"))):
  @property
  def uni (self):
    """
    Returns a "unidirectional" version of this link
    The unidirectional versions of symmetric keys will be equal
    """
    pairs = list(self.end)
    pairs.sort()
    return Link(pairs[0][0],pairs[0][1],pairs[1][0],pairs[1][1])

  @property
  def end (self):
    return ((self[0],self[1]),(self[2],self[3]))

  def __str__ (self):
    return "%s.%s -> %s.%s" % (dpid_to_str(self[0]),self[1],
                               dpid_to_str(self[2]),self[3])

  def __repr__ (self):
    return "Link(dpid1=%s,port1=%s, dpid2=%s,port2=%s)" % (self.dpid1,
        self.port1, self.dpid2, self.port2)


class Discovery (EventMixin):
  """
  Component that attempts to discover network toplogy.
  Sends out specially-crafted LLDP packets, and monitors their arrival.
  """

  _flow_priority = 65000     # Priority of LLDP-catching flow (if any)
  _link_timeout = 10         # How long until we consider a link dead
  _timeout_check_period = 5  # How often to check for timeouts

  _eventMixin_events = set([
    LinkEvent,
  ])

  _core_name = "openflow_discovery" # we want to be core.openflow_discovery

  Link = Link

  def __init__ (self, install_flow = True, explicit_drop = True,
                link_timeout = None, eat_early_packets = False):
    self._eat_early_packets = eat_early_packets
    self._explicit_drop = explicit_drop
    self._install_flow = install_flow
    if link_timeout: self._link_timeout = link_timeout

    self.adjacency = {} # From Link to time.time() stamp
    self._sender = LLDPSender(self.send_cycle_time)

    # Listen with a high priority (mostly so we get PacketIns early)
    core.listen_to_dependencies(self,
        listen_args={'openflow':{'priority':0xffffffff}})

    Timer(self._timeout_check_period, self._expire_links, recurring=True)

  @property
  def send_cycle_time (self):
    return self._link_timeout / 2.0

  def install_flow (self, con_or_dpid, priority = None):
    if priority is None:
      priority = self._flow_priority
    if isinstance(con_or_dpid, (int,long)):
      con = core.openflow.connections.get(con_or_dpid)
      if con is None:
        log.warn("Can't install flow for %s", dpid_to_str(con_or_dpid))
        return False
    else:
      con = con_or_dpid

    match = of.ofp_match(dl_type = pkt.ethernet.LLDP_TYPE,
                          dl_dst = pkt.ETHERNET.NDP_MULTICAST)
    msg = of.ofp_flow_mod()
    msg.priority = priority
    msg.match = match
    msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
    con.send(msg)
    return True

  def _handle_openflow_ConnectionUp (self, event):
    if self._install_flow:
      # Make sure we get appropriate traffic
      log.debug("Installing flow for %s", dpid_to_str(event.dpid))
      self.install_flow(event.connection)

  def _handle_openflow_ConnectionDown (self, event):
    # Delete all links on this switch
    self._delete_links([link for link in self.adjacency
                        if link.dpid1 == event.dpid
                        or link.dpid2 == event.dpid])

  def _expire_links (self):
    """
    Remove apparently dead links
    """
    now = time.time()

    expired = [link for link,timestamp in self.adjacency.iteritems()
               if timestamp + self._link_timeout < now]
    if expired:
      for link in expired:
        log.info('link timeout: %s', link)

      self._delete_links(expired)

  def _handle_openflow_PacketIn (self, event):
    """
    Receive and process LLDP packets
    """

    packet = event.parsed

    if (packet.effective_ethertype != pkt.ethernet.LLDP_TYPE
        or packet.dst != pkt.ETHERNET.NDP_MULTICAST):
      if not self._eat_early_packets: return
      if not event.connection.connect_time: return
      enable_time = time.time() - self.send_cycle_time - 1
      if event.connection.connect_time > enable_time:
        return EventHalt
      return

    if self._explicit_drop:
      if event.ofp.buffer_id is not None:
        log.debug("Dropping LLDP packet %i", event.ofp.buffer_id)
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        event.connection.send(msg)

    lldph = packet.find(pkt.lldp)
    if lldph is None or not lldph.parsed:
      log.error("LLDP packet could not be parsed")
      return EventHalt
    if len(lldph.tlvs) < 3:
      log.error("LLDP packet without required three TLVs")
      return EventHalt
    if lldph.tlvs[0].tlv_type != pkt.lldp.CHASSIS_ID_TLV:
      log.error("LLDP packet TLV 1 not CHASSIS_ID")
      return EventHalt
    if lldph.tlvs[1].tlv_type != pkt.lldp.PORT_ID_TLV:
      log.error("LLDP packet TLV 2 not PORT_ID")
      return EventHalt
    if lldph.tlvs[2].tlv_type != pkt.lldp.TTL_TLV:
      log.error("LLDP packet TLV 3 not TTL")
      return EventHalt

    def lookInSysDesc ():
      r = None
      for t in lldph.tlvs[3:]:
        if t.tlv_type == pkt.lldp.SYSTEM_DESC_TLV:
          # This is our favored way...
          for line in t.payload.split('\n'):
            if line.startswith('dpid:'):
              try:
                return int(line[5:], 16)
              except:
                pass
          if len(t.payload) == 8:
            # Maybe it's a FlowVisor LLDP...
            # Do these still exist?
            try:
              return struct.unpack("!Q", t.payload)[0]
            except:
              pass
          return None

    originatorDPID = lookInSysDesc()

    if originatorDPID == None:
      # We'll look in the CHASSIS ID
      if lldph.tlvs[0].subtype == pkt.chassis_id.SUB_LOCAL:
        if lldph.tlvs[0].id.startswith('dpid:'):
          # This is how NOX does it at the time of writing
          try:
            originatorDPID = int(lldph.tlvs[0].id[5:], 16)
          except:
            pass
      if originatorDPID == None:
        if lldph.tlvs[0].subtype == pkt.chassis_id.SUB_MAC:
          # Last ditch effort -- we'll hope the DPID was small enough
          # to fit into an ethernet address
          if len(lldph.tlvs[0].id) == 6:
            try:
              s = lldph.tlvs[0].id
              originatorDPID = struct.unpack("!Q",'\x00\x00' + s)[0]
            except:
              pass

    if originatorDPID == None:
      log.warning("Couldn't find a DPID in the LLDP packet")
      return EventHalt

    if originatorDPID not in core.openflow.connections:
      log.info('Received LLDP packet from unknown switch')
      return EventHalt

    # Get port number from port TLV
    if lldph.tlvs[1].subtype != pkt.port_id.SUB_PORT:
      log.warning("Thought we found a DPID, but packet didn't have a port")
      return EventHalt
    originatorPort = None
    if lldph.tlvs[1].id.isdigit():
      # We expect it to be a decimal value
      originatorPort = int(lldph.tlvs[1].id)
    elif len(lldph.tlvs[1].id) == 2:
      # Maybe it's a 16 bit port number...
      try:
        originatorPort  =  struct.unpack("!H", lldph.tlvs[1].id)[0]
      except:
        pass
    if originatorPort is None:
      log.warning("Thought we found a DPID, but port number didn't " +
                  "make sense")
      return EventHalt

    if (event.dpid, event.port) == (originatorDPID, originatorPort):
      log.warning("Port received its own LLDP packet; ignoring")
      return EventHalt

    link = Discovery.Link(originatorDPID, originatorPort, event.dpid,
                          event.port)

    if link not in self.adjacency:
      self.adjacency[link] = time.time()
      log.info('link detected: %s', link)
      self.raiseEventNoErrors(LinkEvent, True, link)
    else:
      # Just update timestamp
      self.adjacency[link] = time.time()

    return EventHalt # Probably nobody else needs this event

  def _delete_links (self, links):
    for link in links:
      self.raiseEventNoErrors(LinkEvent, False, link)
    for link in links:
      self.adjacency.pop(link, None)

  def is_edge_port (self, dpid, port):
    """
    Return True if given port does not connect to another switch
    """
    for link in self.adjacency:
      if link.dpid1 == dpid and link.port1 == port:
        return False
      if link.dpid2 == dpid and link.port2 == port:
        return False
    return True


def launch (no_flow = False, explicit_drop = True, link_timeout = None,
            eat_early_packets = False):
  explicit_drop = str_to_bool(explicit_drop)
  eat_early_packets = str_to_bool(eat_early_packets)
  install_flow = not str_to_bool(no_flow)
  if link_timeout: link_timeout = int(link_timeout)

  core.registerNew(Discovery, explicit_drop=explicit_drop,
                   install_flow=install_flow, link_timeout=link_timeout,
eat_early_packets=eat_early_packets)
