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
Basic controller designed

file di prova in cui separo la classe topology

by Matteo Maso & Andrea Pittaro
"""
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
import pox.topology
from pox.openflow.discovery import Discovery
import pox.openflow.topology
from pox.lib.util import dpid_to_str
import pox.host_tracker
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente

import pox.lib.packet as pkt #per analizzare i pacchetti
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import str_to_dpid

import time
import multiprocessing #multiprocess

import my_topo_SDN as mt #classe mia in cui mi memorizzo la topologia'

topo = mt.topo() #topologia mia

log = core.getLogger()

def _handle_LinkEvent(event):
    """
    acquisisce gli eventi di tipo LinkEvent della classe openflow.discovery
    """
    l = event.link
    if event.added:
        log.debug('LinkAdd dpid1: {0} porta {1}, dpid2: {2} porta {3}'.format(l.dpid1, l.port1, l.dpid2, l.port2))
        topo.add_link(l.dpid1, l.port1, l.dpid2, l.port2)
    elif event.removed:
        log.debug('LinkRemoved dpid1: {0} porta {1}, dpid2: {2} porta {3}'.format(l.dpid1, l.port1, l.dpid2, l.port2))
        topo.rm_link(l.dpid1, l.port1, l.dpid2, l.port2)
    else:
        pass

def _handle_HostEvent(event):
    """
    handle HostEvent from discovery
    """
    mac_host = event.entry.macaddr
    dpid_sw = event.entry.dpid
    dpid_port = event.entry.port
    key1 = event.entry.ipAddrs.keys()
    if event.join:
        if len(key1) > 0:
            host_ip = key1[0]
            topo.add_host(dpid_sw, mac_host, dpid_port, host_ip)
            log.debug("from host event %s", host_ip)
        else:
            pass #no ip i have only mac
    elif event.leave:
        pass

def _handle_ConnectionUp (event):
    topo.add_switch(event.connection.dpid)
    log.debug("Add switch: %s", dpid_to_str(event.connection.dpid))



def _handle_PacketIn(event):
    """
    qui quando due host vogliono comunicare
    vado ad inserire la rotta di default
    """
    packet = event.parsed #this is the parsed packet data
    log.debug("_handle_PacketIn")
    src_mac = packet.src	#mac del sorgente del pacchetto
    dst_mac = packet.dst	#mac del destinatario del pacchetto
    portIn = event.port


    if packet.type == packet.ARP_TYPE:
        #log.debug("ARP_TYPE packet arrived")
        if packet.payload.opcode == arp.REQUEST:
            ip_src = packet.payload.protosrc
            ip_dst = packet.payload.protodst

            if topo.ip_connected(ip_src, ip_dst):
                #installa le rotte di default con la minimum path
                log.debug("path presente")
                topo.add_default_path(ip_src, ip_dst)
            else:
                #i due host non sono connessi quindi o devo cercare il secondo
                #trovare un modo, per ora possono comunicare solo se hanno gia' fatto un tentativo di accesso alla related
                log.debug("path NON presente")


    elif packet.type == packet.IP_TYPE:
        ip_packet = packet.find('ipv4')
        log.debug("IP_TYPE packet arrived")
        ip_src = ip_packet.srcip #ip sorgente
        ip_dst = ip_packet.dstip #ip destinatario

        #connessione alla rete
        if ip_packet.dstip == IPAddr('10.10.0.0'):
            topo.add_host(event.connection.dpid, src_mac, event.port, ip_packet.srcip)

#devo farlo solo per i pacchetti icmp e arp per altri tipi di flusso mettere metodi separate
        if topo.ip_connected(ip_src, ip_dst):
            #installa le rotte di default con la minimum path
            log.debug("path presente")
            topo.add_default_path(ip_src, ip_dst)
        else:
            #i due host non sono connessi quindi o devo cercare il secondo
            #trovare un modo, per ora possono comunicare solo se hanno gia' fatto un tentativo di accesso alla related
            log.debug("path NON presente")


def _show_topo():
    """
    function to show the graph on a separate process
    funzione da sistemare, il multirocesso in questo caso non e' necessario

    """
    job_for_another_core = multiprocessing.Process(target=topo.save_graph,args=()) #chiama la funzione save_graph in un processo separato
    job_for_another_core.start()

def launch():
    """
    start:
        pox.topology.launch()
        pox.openflow.discovery.launch()
        pox.openflow.topology.launch()
        pox.host_tracker.launch()

    and make listeners functions
    """
    pox.topology.launch()
    pox.openflow.discovery.launch()
    pox.openflow.topology.launch()
    #pox.host_tracker.launch()
    core.openflow_discovery.addListenerByName("LinkEvent", _handle_LinkEvent)
    #core.host_tracker.addListenerByName("HostEvent", _handle_HostEvent)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    core.openflow.addListenerByName("ConnectionUp",_handle_ConnectionUp)


    Timer(2, _show_topo, recurring=True) #every 2 seconds execute _show_topo
