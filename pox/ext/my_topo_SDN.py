#classe topo SDN
#che utilizzo nel mio controller
from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr

#import ipaddress as Ip
import networkx as nx            #graph library
import matplotlib.pyplot as plt  #for ploting graph

import random #debug

log = core.getLogger()
switch = {} #dizionario di switch dpid e' la chiave
grafo = nx.Graph()          #grafo con vari attributi
pck_error_gf = nx.Graph()    #grafo pesato secondo il pathloss
#delay_gf = nx.Graph()       #delay del link
capacity_gf = nx.Graph()    #capacita' max link
load_gf = nx.Graph()        #percentuale del caricamento del link in base alla sua capacita' max
ip_to_switch = {} #dizionario in cui l'ip solo le chiavi e i valori gli elementi switch
mac_to_ip = {} #per gli host

__DEFAULT_RULES_PRIORITY = 50
__DEFAULT_ARP_PATH = 150
__DEFAULT_IP_PATH = 1000

def add_host(dpid, mac, port, ip):
    """
    add host on the graph and the port of switch
    """
    #devo aggiungere le porte allo switch
    #da finire
    if switch.has_key(dpid): #se switch e' presente
        switch[dpid].add_host(mac, port, ip)
        mac_to_ip[mac] = ip
        ip_to_switch[ip] = switch[dpid]
        grafo.add_node(ip)
        pck_error_gf.add_node(ip)
        #delay_gf.add_node(ip)
        capacity_gf.add_node(ip)
        load_gf.add_node(ip)

        grafo.add_edge(dpid, ip)
        pck_error_gf.add_edge(dpid, ip, weight=0)
        #delay_gf.add_edge(dpid, ip, weight=1)
        capacity_gf.add_edge(dpid, ip, weight=10)
        load_gf.add_edge(dpid, ip, weight=0)
        log.debug("add host %s", ip)
    else:
        log.warning("Add host to switch that don't exist")

def add_switch(dpid):
    """
    Add a switch if it wasn't already added
    """
    if switch.has_key(dpid):
        pass
    else:
        switch[dpid] = my_Switch(dpid)
        grafo.add_node(dpid)
        pck_error_gf.add_node(dpid)
        #delay_gf.add_node(dpid)
        capacity_gf.add_node(dpid)
        load_gf.add_node(dpid)
        log.debug("Add switch: %s", dpid_to_str(dpid))
        add_default_rules(dpid)
def rm_switch(dpid):
    grafo.remove_node(dpid)
    pck_error_gf.remove_node(dpid)
    #delay_gf.add_node(dpid)
    capacity_gf.remove_node(dpid)
    load_gf.remove_node(dpid)
    del switch[dpid] #remove the disconnected switch

def save_graph():
    pos=nx.spring_layout(grafo) # positions for all nodes
    nx.draw_networkx(grafo,pos, with_labels=True, node_size=700, width=6, font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("grafo.png")      #salva l'immagine
    plt.clf()                     #elimina l'immagine corrente dalla libreria

    edge_labels=nx.draw_networkx_edge_labels(pck_error_gf,pos,font_size=12)
    nx.draw_networkx(pck_error_gf,pos, with_labels=True,node_color='green',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("pck_error_gf.png")   #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria

    # edge_labels2=nx.draw_networkx_edge_labels(delay_gf,pos,font_size=12)
    # nx.draw_networkx(pck_error_gf,pos, with_labels=True,node_color='blue',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    # plt.axis('off')
    # plt.savefig("delay_gf.png")      #salva l'immagine
    # plt.clf()                        #elimina l'immagine corrente dalla libreria

    edge_labels3=nx.draw_networkx_edge_labels(capacity_gf,pos,font_size=12)
    nx.draw_networkx(pck_error_gf,pos, with_labels=True,node_color='gray',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("capacity_gf.png")      #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria

    edge_labels4=nx.draw_networkx_edge_labels(load_gf,pos,font_size=12)
    nx.draw_networkx(pck_error_gf,pos, with_labels=True,node_color='gray',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("load_gf.png")      #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria


def add_link(dpid1, port1, dpid2, port2):
    """
    Inside add_link function, add switch and link
    """
    add_switch(dpid1)
    add_switch(dpid2)
    switch[dpid1].port_dpid[port1] = dpid2
    switch[dpid1].dpid_port[dpid2] = port1
    switch[dpid2].port_dpid[port2] = dpid1
    switch[dpid2].dpid_port[dpid1] = port2
    grafo.add_edge(dpid1, dpid2)
    pck_error_gf.add_edge(dpid1, dpid2, weight=10)
    #delay_gf.add_edge(dpid1, dpid2, weight=1)
    capacity_gf.add_edge(dpid1, dpid2, weight=10)
    load_gf.add_edge(dpid1, dpid2, weight=0)

def rm_link(dpid1, port1, dpid2, port2):
    x = True
    try:
        grafo.remove_edge(dpid1, dpid2)
        pck_error_gf.remove_edge(dpid1, dpid2)
        #delay_gf.add_edge(dpid1, dpid2)
        capacity_gf.add_edge(dpid1, dpid2)
        load_gf.add_edge(dpid1, dpid2)
    except:
        #se tento di rimuovere un link che non e' presente nel grafo
        x = False
    if x:
        del switch[dpid1].port_dpid[port1]
        del switch[dpid1].dpid_port[dpid2]

        del switch[dpid2].port_dpid[port2]
        del switch[dpid2].dpid_port[dpid1]

# def link_delay(dpid1, dpid2, value):
#     """
#     modifica il peso del link del grafo delay_gf
#     """
#     delay_gf[dpid1][dpid2]['weight']=value

def link_pck_error(dpid1, dpid2, value):
    """
    modifica il peso del link del grafo pck_error_gf
    """
    pck_error_gf[dpid1][dpid2]['weight']=value

def link_load(dpid1, dpid2, value):
    """
    modifica il peso del link del grafo load_gf
    """
    load_gf[dpid1][dpid2]['weight']=value

def link_capacity(dpid1, dpid2, value):
    """
    modifica il peso del link del grafo capacity_gf
    """
    capacity_gf[dpid1][dpid2]['weight']=value

def add_default_path(ip_src, ip_dst):
    #sw_list = nx.shortest_path(pck_error_gf,source=ip_src, target=ip_dst)
    sw_list = nx.dijkstra_path(pck_error_gf, source=ip_src, target=ip_dst, weight='weight')
    log.debug(sw_list) #show minimum path
    for i in range (1, len(sw_list) - 2):
        #installo i flussi da ip_src a ip_dst
        msg = of.ofp_flow_mod()
        msg.priority = __DEFAULT_IP_PATH
        msg.match.nw_dst = IPAddr(str(ip_dst))
        msg.match.dl_type = 0x800 #ip
        pt_next_hope = switch[sw_list[i]].dpid_port[sw_list[i+1]]
        msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
        core.openflow.sendToDPID(sw_list[i], msg) #switch i-esimo

        msg = of.ofp_flow_mod()
        msg.priority = __DEFAULT_ARP_PATH
        msg.match.dl_type = 0x806 #arp reques
        msg.match.nw_dst = IPAddr(str(ip_dst))
        msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
        core.openflow.sendToDPID(sw_list[i], msg)

    for i in range (2, len(sw_list) - 1):
        #installo i flussi da ip_dst a ip_src
        msg = of.ofp_flow_mod()
        msg.priority = __DEFAULT_IP_PATH
        msg.match.nw_dst = IPAddr(str(ip_src))
        msg.match.dl_type = 0x800 #ip
        pt_pre_hope = switch[sw_list[i]].dpid_port[sw_list[i-1]]
        msg.actions.append(of.ofp_action_output(port = pt_pre_hope ))
        core.openflow.sendToDPID(sw_list[i], msg) #switch i-esimo

        msg = of.ofp_flow_mod()
        msg.priority = __DEFAULT_ARP_PATH
        msg.match.dl_type = 0x806 #arp reques
        msg.match.nw_dst = IPAddr(str(ip_src))
        msg.actions.append(of.ofp_action_output(port = pt_pre_hope ))
        core.openflow.sendToDPID(sw_list[i], msg)

def add_default_rules(dpid):
    """
    add default rules on new switch
    arp request flooding
    """
    msg = of.ofp_flow_mod()
    msg.priority = __DEFAULT_RULES_PRIORITY
    msg.match.dl_type = 0x806 #arp reques
    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD ))
    core.openflow.sendToDPID(dpid, msg)

    #MORE DEFAULT RULES

def ip_connected(ip1, ip2):
    try:
        nx.has_path(grafo, source=ip1, target=ip2)
    except:
        return False
    return True

def is_logged(ip1):
    if ip_to_switch.has_key(ip1):
        return True
    else:
        return False

class my_Switch():
    def __init__(self, dpid):
        self.dpid = dpid
        self.dpid_port = {}  #chiave dpid/ip valore porta
        self.port_dpid = {}
        self.port_mac = {}
        self.mac_port = {}
        self.port_capacity={} # maximum port capacity in Mbps
        self.host_gaming={} # if port has a gaming host, value is True
        self.heavy_traffic={} # if port has an host who is making a lot of traffic, here is true

    def add_host(self, mac, porta, ip):
        "add host on the switch's port"
        if self.dpid_port.has_key(ip):
            log.debug("IP still exist on the switch")
        else:
            self.dpid_port[ip] = porta
            self.port_dpid[porta] = ip
            self.port_mac[porta] = mac
            self.mac_port[mac] = porta

            msg = of.ofp_flow_mod()
            msg.priority = 100
            msg.match.dl_type = 0x806 #arp reques
            msg.match.dl_dst = EthAddr(str(mac))
            msg.actions.append(of.ofp_action_output(port = porta ))
            core.openflow.sendToDPID(self.dpid, msg)

            msg = of.ofp_flow_mod()
            msg.priority = 1000
            msg.match.nw_dst = IPAddr(str(ip))
            msg.match.dl_type = 0x800 #ip
            msg.actions.append(of.ofp_action_output(port = porta ))
            core.openflow.sendToDPID(self.dpid, msg)
