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

import my_topo_SDN as topo #new class

log = core.getLogger()

SDN_network = "10.0.0.0/24"

PCK_ERROR_OPT = 1
DELAY_OPT     = 2
DEFAULT_OPT   = 3

def _handle_LinkEvent(event):
    """
    handle event ("LinkEvent") from openflow.discovery
    """
    l = event.link
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
    log.debug("Add switch: %s", dpid_to_str(event.connection.dpid))

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

    ip_src = ip_pck.srcip #ip sorgente
    ip_dst = ip_pck.dstip #ip destinatario

    if (IP.IPv4Address(ip_src) == IP.IPv4Address('100.100.100.0') or IP.IPv4Address(ip_src) == IP.IPv4Address('100.100.100.1')):
        """ pacchetti di controllo """
        #non esegue nulla in quanto se ne occupa network_performance
        pass
    elif (IP.IPv4Address(ip_src) in IP.IPv4Network(SDN_network)):
        """ sorgente e' nella sotto rete SDN """
        #verifico se gia' presente nel grafo
        if (topo.is_logged(ip_src)): #se non e' presente lo aggiungo
            pass
        else:
            topo.add_host(event.connection.dpid, src_mac, event.port, ip_pck.srcip)
            log.debug("\n %s aggiunto nella rete", ip_src)

        if (IP.IPv4Address(ip_dst) in IP.IPv4Network(SDN_network)):
            """ destinatario nella sotto rete SDN """
            if topo.is_logged(ip_dst):
                #destinatario presente posso farli connettere
                if topo.ip_connected(ip_src, ip_dst):
                    #installa le rotte di default con la minimum path
                    #scegliere la path in base a qualche metrica particolare
                    topo.add_path(ip_src, ip_dst, DEFAULT_OPT)
                else:
                    log.debug("Some errors occur in the graph path")
            else:
                #destinatario interno non ancora loggato, potrei cercarlo ma per ora no
                log.debug("Ip_dst interno ma non ancora loggato: %s", ip_dst)

        else:
            """ destinatario fuori dalla sottorete SDN """
            #lo indirizzo nel gateway di default
            topo.add_path_to_gw(ip_src, ip_dst, DEFAULT_OPT)
    else:
        """ sorgente del pacchetto proveniente dall'esterno della sottorete SDN """
        if topo.is_logged(ip_dst):
            #destinatario presente posso farli connettere
            topo.add_path_to_gw(ip_src, ip_dst, DEFAULT_OPT)
        else:
            #destinatario interno non ancora loggato, potrei cercarlo ma per ora no
            log.debug("Ip_dst interno ma non ancora loggato: %s", ip_dst)

def _show_topo():
    """
    function to show the graph on a separate process
    """
    job_for_another_core = multiprocessing.Process(target=topo.save_graph,args=()) #chiama la funzione save_graph in un processo separato
    job_for_another_core.start()

def launch():
    """
    start:
        pox.topology.launch()
        pox.openflow.discovery
        pox.openflow.topology
        pox.openflow.spanning_tree
    and make listeners functions
    """
    pox.topology.launch()
    pox.openflow.discovery.launch()
    pox.openflow.topology.launch()
    pox.openflow.spanning_tree.launch()
    core.openflow_discovery.addListenerByName("LinkEvent", _handle_LinkEvent)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    core.openflow.addListenerByName("ConnectionUp",_handle_ConnectionUp)
    core.openflow.addListenerByName("ConnectionDown",_handle_ConnectionDown)

    Timer(5, _show_topo, recurring=True) #every 2 seconds execute _show_topo
