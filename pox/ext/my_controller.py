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

"""
Controller
by Matteo Maso & Andrea Pittaro
"""
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
import pox.topology
from pox.openflow.discovery import Discovery
import pox.openflow.topology
import pox.openflow.spanning_tree
from pox.lib.util import dpid_to_str
import pox.host_tracker
from pox.lib.recoco import Timer  #for recoursive functions
import pox.lib.packet as pkt
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import str_to_dpid
import ipaddress as IP
import multiprocessing #multiprocess
import datetime

import my_topo_SDN as topo #new class
import graphUpdater as gu
log = core.getLogger()

# SDN_network = "10.0.0.0/24"
# SDN_NETMASK = "255.255.255.0"
SDN_network = ""#"192.168.0.0/16"

PCK_ERROR_OPT = 1
DELAY_OPT     = 2
DEFAULT_OPT   = 3
hasGateway    = False
hasNetwork    = False
EXTERNAL = None
unknown_link = []
recent_packets = []

def _handle_LinkEvent(event):
    """
    handle event ("LinkEvent") from openflow.discovery
    """
    l = event.link
    #if there's a link, the controller knows the link between switches
    for i,c in enumerate(unknown_link):
        if c[0] == l.dpid1:
            try:
                dpid2 = switch[c[0]].port_dpid[c[1]]
                topo.link_capacity(c[0],dpid2, c[2])
                del unknown_link[i]# remove unknown link from the list
            except:
                break # doesn't have the other link yet
        elif c[0] == l.dpid2:
            try:
                dpid = switch[c[0]].port_dpid[c[1]]
                topo.link_capacity(c[0],dpid, c[2])
                del unknown_link[i] # remove unknown link from the list
            except:
                break # doesn't have the other link yet
        else:
            continue
    if event.added:
        log.debug('LinkAdd dpid1: {0} porta {1}, dpid2: {2} porta {3}'.format(l.dpid1, l.port1, l.dpid2, l.port2))
        topo.add_link(l.dpid1, l.port1, l.dpid2, l.port2)
    elif event.removed:
        log.debug('LinkRemoved dpid1: {0} porta {1}, dpid2: {2} porta {3}'.format(l.dpid1, l.port1, l.dpid2, l.port2))
        topo.rm_link(l.dpid1, l.port1, l.dpid2, l.port2)

def _handle_ConnectionUp (event): #capire se nella pratica si logga anche lo switch legacy
    """
    handle connection up from switch
    """
    topo.add_switch(event.connection.dpid)
    for port in event.ofp.ports:
        if ((port.state & of.ofp_port_state_rev_map["OFPPS_LINK_DOWN"]) and (port.port_no<10000)):
             log.info("port %i  is down",port.port_no)
        #check only current status. ignore maximum status. it's more realistic
        if(port.curr & of.ofp_port_features_rev_map["OFPPF_10MB_HD"] or
                port.curr & of.ofp_port_features_rev_map["OFPPF_10MB_FD"]):
            topo.switch[event.connection.dpid].port_capacity[port.port_no] = 10; #TODO constants
            try:
                topo.link_capacity(event.connection.dpid,topo.switch[event.connection.dpid].port_dpid[port.port_no],10)
            except:
                unknown_link.append([event.connection.dpid, port.port_no, 10])
            log.info("port %i is a 10Mbps",port.port_no)
        elif(port.curr & of.ofp_port_features_rev_map["OFPPF_100MB_HD"] or
            port.curr & of.ofp_port_features_rev_map["OFPPF_100MB_FD"]):
            topo.switch[event.connection.dpid].port_capacity[port.port_no] = 100; #TODO constants
            try:
                topo.link_capacity(event.connection.dpid,topo.switch[event.connection.dpid].port_dpid[port.port_no],100)
            except:
                unknown_link.append([event.connection.dpid, port.port_no, 100])
            log.info("port %i is a 100Mbps",port.port_no)
        elif(port.curr & of.ofp_port_features_rev_map["OFPPF_1GB_HD"] or
            port.curr & of.ofp_port_features_rev_map["OFPPF_1GB_FD"]):
            topo.switch[event.connection.dpid].port_capacity[port.port_no] = 1000; #TODO constants
            try:
                topo.link_capacity(event.connection.dpid,topo.switch[event.connection.dpid].port_dpid[port.port_no],1000)
            except:
                unknown_link.append([event.connection.dpid, port.port_no, 1000])
            log.info("port %i is a 1Gbps",port.port_no)
        elif(port.curr & of.ofp_port_features_rev_map["OFPPF_10GB_FD"]):
            topo.switch[event.connection.dpid].port_capacity[port.port_no] = 10000; #TODO constants
            try:
                topo.link_capacity(event.connection.dpid,topo.switch[event.connection.dpid].port_dpid[port.port_no],10000)
            except:
                unknown_link.append([event.connection.dpid, port.port_no, 10000])
            log.info("port %i is a 10Gbps",port.port_no)

        #Find the port where is connected the standard router
        if hasGateway  and port.hw_addr == topo.hosts[0].mac: #is the switch with route to internet
            log.info("found port to the internet")
            EXTERNAL = (event.dpid,port.port_no)
            topo.hosts[0].switch=EXTERNAL
            topo.hosts[0].mac=EthAddr("FF:FF:FF:FF:FF:FF") # broadcast mac
            sw  = event.dpid in topo.switch #switch already added, so it exist
            sw.port_dpid[port.port_no] = IPAddr("0.0.0.0",0)
            sw.dpid_port[IPAddr("0.0.0.0",0)]=port.port_no
            #probably useless
            sw.port_mac[port.port_no]=port.hw_addr
            sw.mac_port[port.hw_addr]=port.port_no
            #add the link to the external
            topo.add_link(event.dpid,port.port_no,topo.hosts[0].ip,port.port_no,isHost=True)
            #all ip_dst == external through port
            topo.add_default_ext_rules(event.connection.dpid, SDN_network, port)

        #default rules
        # if SDN_network != "": # I set the default network
        #     topo.add_default_rules(event.connection.dpid, SDN_network)


    #verificare che sua uno switch openflow
    log.debug("Add switch: %s", dpid_to_str(event.connection.dpid))

def _handle_port_status(event):
        if not event.modified :
            return
        for port in event.desc:
            if ((port.state & of.ofp_port_state_rev_map["OFPPS_LINK_DOWN"]) and (port.port_no<10000)):
                 log.info("port %i  is down",port.port_no)
            #check only current status. ignore maximum status. it's more realistic
            if(port.curr & of.ofp_port_features_rev_map["OFPPF_10MB_HD"] or
                    port.curr & of.ofp_port_features_rev_map["OFPPF_10MB_FD"]):
                topo.switch[event.connection.dpid].port_capacity[port.port_no] = 10; #TODO constants
                log.info("port %i changed to 10Mbps",port.port_no)
            elif(port.curr & of.ofp_port_features_rev_map["OFPPF_100MB_HD"] or
                port.curr & of.ofp_port_features_rev_map["OFPPF_100MB_FD"]):
                topo.switch[event.connection.dpid].port_capacity[port.port_no] = 100; #TODO constants
                log.info("port %i changed to 100Mbps",port.port_no)
            elif(port.curr & of.ofp_port_features_rev_map["OFPPF_1GB_HD"] or
                port.curr & of.ofp_port_features_rev_map["OFPPF_1GB_FD"]):
                topo.switch[event.connection.dpid].port_capacity[port.port_no] = 1000; #TODO constants
                log.info("port %i changed to 1Gbps",port.port_no)
            elif(port.curr & of.ofp_port_features_rev_map["OFPPF_10GB_FD"]):
                topo.switch[event.connection.dpid].port_capacity[port.port_no] = 10000; #TODO constants
                log.info("port %i is a 10Gbps",port.port_no)


def _handle_ConnectionDown(event):
    topo.rm_switch(event.connection.dpid)
    log.debug("Rem switch: %s", dpid_to_str(event.connection.dpid))

def _handle_PacketIn(event):
    packet = event.parsed       #this is the parsed packet data
    src_mac = packet.src	    #mac del sorgente del pacchetto
    dst_mac = packet.dst	    #mac del destinatario del pacchetto

    if packet.type == packet.ARP_TYPE:

        _handle_arp_packet(event)

    elif packet.type == packet.IP_TYPE:

        _handle_ip_packet(event)


def _handle_arp_packet(event):
    packet = event.parsed

    if packet.payload.opcode == arp.REQUEST:
        ip_src = packet.payload.protosrc
        ip_dst = packet.payload.protodst

def _handle_ip_packet(event):

    packet = event.parsed
    src_mac = packet.src	    #mac del sorgente del pacchetto
    dst_mac = packet.dst	    #mac del destinatario del pacchetto
    ip_pck = packet.find('ipv4')
    if ip_pck is None:
        log.debug("ip_pck no ipv4")


    ip_src = IPAddr(ip_pck.srcip) #ip sorgente
    ip_dst = IPAddr(ip_pck.dstip) #ip destinatario

    print ("src=%s dst = %s",ip_src , ip_dst)
    for h in topo.hosts:
        if h.ip == ip_src:
            if h.switch != event.connection.dpid: # switch ip src and dst as pox do wrong
                a= ip_src
                ip_src = ip_dst
                ip_dst = a

    for i,pkt in enumerate(recent_packets):
        if pkt[0] == ip_src and pkt[1]==ip_dst and pkt[2] == event.dpid:
            return # it's a flooded packet that reached controller
        # elif pkt[0] == ip_dst and pkt[1]==ip_src and pkt[2] ==event.dpid: #packet arrives in order of flood.
            #faulty links will be deleted by discovery
            #topo.add_link(event.connection.dpid,event.port,pkt[2],pkt[3])
            # try:
            #     topo.add_path(ip_src,ip_dst,topo.LOAD_OPT)
            # except:
            #     del recent_packets[i] # discovery with tests
        else:
            delta = datetime.datetime.now()- pkt[4]
            if  delta.seconds > 2: # after 10 seconds the packet is no more flooded
                del recent_packets[i]

    if (IPAddr(ip_src) == IPAddr('100.100.100.0') or IPAddr(ip_src) == IPAddr('100.100.100.1')):
        return;
    #internal packet to ext
    if type(EXTERNAL) is tuple and not ip_dst.inNetwork(SDN_network[0],netmask=SDN_network[1]) :
        msg=of.ofp_packet_out()
        msg.data = event.parsed
        msg.action.append(of.ofp_action_output(port=EXTERNAL[1]))
        core.openflow.sendToDPID(EXTERNAL[0],msg) #send packet outside, then continue with adding path to external

    srcH = None
    dstH = None
    # alreadySrc = False
    # alreadyDst=False
    #
    if (topo.is_logged(ip_src)): #se non e' presente lo aggiungo
        if hasNetwork and ip_dst.inNetwork(SDN_network) and topo.is_logged(ip_dst):
            topo.add_path(ip_src,ip_dst,LOAD_OPT)
        elif hasNetwork and not ip_dst.inNetwork(SDN_network):
            topo.add_path_through_gw(ip_src,ip_dst,LOAD_OPT)
        else: #is in network, but I don't know where it is. Controlled flood
            recent_packets.append([ip_src,ip_dst,event.connection.dpid,event.port,datetime.datetime.now()])
            msg = of.ofp_packet_out()
            msg.data = event.parsed
            msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL))
            core.openflow.sendToDPID(event.connection.dpid,msg)
    else:
        topo.add_host(event.connection.dpid, src_mac, event.port, ip_src)
        for h in topo.hosts:
            if(h.ip == ip_src):
                h.addConnection(ip_dst)
        if hasNetwork and ip_dst.inNetwork(SDN_network) and topo.is_logged(ip_dst):
            topo.add_path(ip_src,ip_dst,LOAD_OPT)
        elif hasNetwork and not ip_dst.inNetwork(SDN_network):
            topo.add_path_through_gw(ip_src,ip_dst,LOAD_OPT)
        else: #is in network, but I don't know where it is. Controlled flood
            recent_packets.append([ip_src,ip_dst,event.connection.dpid,event.port,datetime.datetime.now()])
            msg = of.ofp_packet_out()
            msg.data = event.parsed
            msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL))
            core.openflow.sendToDPID(event.connection.dpid,msg)
        log.debug("\n %s aggiunto nella rete", ip_src)


def _show_topo():
    """
    function to show the graph on a separate process
    """
    job_for_another_core = multiprocessing.Process(target=topo.save_graph,args=()) #chiama la funzione save_graph in un processo separato
    job_for_another_core.start()


def launch(__INSTANCE__=None, **kw):
    """
    start:
        pox.topology.launch()
        pox.openflow.discovery
        pox.openflow.topology
        pox.openflow.spanning_tree
    and make listeners functions
    """
    #copied from log.level and adapted to accept mac addr
    #the first host in topo.hosts is theinternet way
    for k,v in kw.iteritems():
        if k.find("mac")>-1: #index -1 is the NotFound
            # print("parsing mac addr")
            log.debug("parsing mac address")
            if len(v) == 17 : # "00:11:22:33:44:55:66" is the mac address form
                h=topo.Host(None,None,ipAddr=IPAddr("0.0.0.0",0),macAddr=EthAddr(v)) # same mac as the port. the ip is a special one. There is no dpid yet
                topo.hosts.append(h) # add the host as the first one
                # print("added ext host" )
                log.info("added the external host and ready for finding the switch/port to which forward all external packets")
        elif k.find("net")>-1 :
            log.debug("parsing network address")
            if len(v) >=9 and len(v)<=18 : # "192.168.240.240/24" is the net address form
                n = v.split('/') # divide the cidr notation
                SDN_network = (IPAddr(n[0]),int(n[1])) # tuple
                # print("added ext host" )
                log.info("added the internal network address %s/%i", n[0],int(n[1]))

    pox.topology.launch()
    pox.openflow.discovery.launch()
    pox.openflow.topology.launch()
    pox.openflow.spanning_tree.launch()
    core.openflow_discovery.addListenerByName("LinkEvent", _handle_LinkEvent)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    core.openflow.addListenerByName("ConnectionUp",_handle_ConnectionUp)
    core.openflow.addListenerByName("ConnectionDown",_handle_ConnectionDown)
    core.openflow.addListenerByName("PortStatus",_handle_port_status)

    Timer(5, _show_topo, recurring=True) #every 2 seconds execute _show_topo
#    Timer(30, topo.ipCleaner, recurring = True) # every 30s clean the old connection ip
    Timer(30, gu.checkChanges, recurring = True) # change the graph if something happened
