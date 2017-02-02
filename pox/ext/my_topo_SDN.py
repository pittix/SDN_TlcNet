#classe topo SDN
#che utilizzo nel mio controller
from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr

#import ipaddress as Ip
import networkx as nx            #graph library
import matplotlib.pyplot as plt  #for ploting graph
import datetime #for connection expiration in host tuples
import random #debug


log = core.getLogger()
switch = {} #dizionario di switch dpid e' la chiave
grafo = nx.Graph()          #grafo con vari attributi
switch_gf = nx.Graph()      #grafo con solo gli switch
pck_error_min_gf = nx.Graph()    #grafo pesato secondo il pathloss
pck_error_max_gf = nx.Graph()    #grafo pesato secondo il complementarepathloss
delay_gf = nx.Graph()       #delay del link
capacity_gf = nx.Graph()    #capacita' max link
load_gf = nx.Graph()        #percentuale del caricamento del link in base alla sua capacita' max
ip_to_switch = {} #dizionario in cui l'ip solo le chiavi e i valori gli elementi switch
mac_to_ip = {} #per gli host
hosts=[] # list of object of type Host

__DEFAULT_RULES_PRIORITY = 50
__DEFAULT_ARP_PATH = 150
__DEFAULT_IP_PATH = 1000
__DEFAULT_EXT_NET_RULE=10
__DEFAULT_INT_NET_RULE= 30

IP_TIMEOUT = 60 #seconds
PCK_ERROR_MIN_OPT = 1
PCK_ERROR_MAX_OPT = 4
DELAY_OPT     = 2
DEFAULT_OPT   = 3
LOAD_OPT      = 5

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
        pck_error_max_gf.add_node(ip)
        pck_error_min_gf.add_node(ip)
        capacity_gf.add_node(ip)
        load_gf.add_node(ip)

        grafo.add_edge(dpid, ip)
        pck_error_min_gf.add_edge(dpid, ip, weight=0)
        pck_error_max_gf.add_edge(dpid, ip, weight=0)
        capacity_gf.add_edge(dpid, ip, weight=0)
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
        pck_error_min_gf.add_node(dpid)
        delay_gf.add_node(dpid)
        capacity_gf.add_node(dpid)
        load_gf.add_node(dpid)
        switch_gf.add_node(dpid)
        log.debug("Add switch: %s", dpid_to_str(dpid))
        add_default_rules(dpid)
def rm_switch(dpid):
    grafo.remove_node(dpid)
    pck_error_min_gf.remove_node(dpid)
    pck_error_max_gf.remove_node(dpid)
    delay_gf.add_node(dpid)
    capacity_gf.remove_node(dpid)
    switch_gf.remove_node(dpid)
    load_gf.remove_node(dpid)
    del switch[dpid] #remove the disconnected switch

def save_graph(counter):


    pos=nx.spring_layout(grafo) # positions for all nodes
    nx.draw_networkx(grafo,pos, with_labels=True, node_size=700, width=6, font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')

    plt.savefig("grafo%i.png" % (counter))      #salva l'immagine
    plt.clf()                     #elimina l'immagine corrente dalla libreria

    edge_labels=nx.draw_networkx_edge_labels(pck_error_min_gf,pos,font_size=12)
    nx.draw_networkx(pck_error_min_gf,pos, with_labels=True,node_color='green',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("pck_error_min_gf%i.png" % (counter))   #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria

    edge_labels=nx.draw_networkx_edge_labels(pck_error_max_gf,pos,font_size=12)
    nx.draw_networkx(pck_error_max_gf,pos, with_labels=True,node_color='green',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("pck_error_max_gf%i.png" % (counter))   #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria


    edge_labels2=nx.draw_networkx_edge_labels(delay_gf,pos,font_size=12)
    nx.draw_networkx(delay_gf,pos, with_labels=True,node_color='blue',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("delay_gf%i.png" % (counter))      #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria

    edge_labels3=nx.draw_networkx_edge_labels(capacity_gf,pos,font_size=12)
    nx.draw_networkx(capacity_gf,pos, with_labels=True,node_color='gray',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("capacity_gf%i.png" % (counter))      #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria

    edge_labels3=nx.draw_networkx_edge_labels(switch_gf,pos,font_size=12)
    nx.draw_networkx(switch_gf,pos, with_labels=True,node_color='gray',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("switch_gf%i.png" % (counter))      #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria

    edge_labels4=nx.draw_networkx_edge_labels(load_gf,pos,font_size=12)
    nx.draw_networkx(load_gf,pos, with_labels=True,node_color='gray',node_size=700, width=6,font_size=20,font_family='sans-serif')    #stampa anche il grafo
    plt.axis('off')
    plt.savefig("load_gf%i.png" % (counter))      #salva l'immagine
    plt.clf()                        #elimina l'immagine corrente dalla libreria


def add_link(dpid1, port1, dpid2, port2, isHost=False):
    """
    Inside add_link function, add switch and link
    """
    add_switch(dpid1)
    add_switch(dpid2)
    switch[dpid1].port_dpid[port1] = dpid2
    switch[dpid1].dpid_port[dpid2] = port1
    if not isHost: # do the reverse only if the other is a switch
        switch[dpid2].port_dpid[port2] = dpid1
        switch[dpid2].dpid_port[dpid1] = port2
    grafo.add_edge(dpid1, dpid2)
    pck_error_min_gf.add_edge(dpid1, dpid2, weight=0)
    pck_error_max_gf.add_edge(dpid1, dpid2, weight=0)
    delay_gf.add_edge(dpid1, dpid2, weight=1)
    switch_gf.add_edge(dpid1, dpid2, weight=1)
    capacity_gf.add_edge(dpid1, dpid2, weight=0)
    load_gf.add_edge(dpid1, dpid2, weight=0)

def rm_link(dpid1, port1, dpid2, port2):
    x = True
    try:
        grafo.remove_edge(dpid1, dpid2)
        pck_error_min_gf.remove_edge(dpid1, dpid2)
        pck_error_max_gf.remove_edge(dpid1, dpid2)
        delay_gf.add_edge(dpid1, dpid2)
        switch_gf.add_edge(dpid1, dpid2)
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

def link_delay(dpid1, dpid2, value):
    """
    modifica il peso del link del grafo delay_gf
    """
    delay_gf[dpid1][dpid2]['weight']=value

def link_pck_error(dpid1, dpid2, value):
    """
    modifica il peso del link del grafo pck_error_gf
    """
    pck_error_min_gf[dpid1][dpid2]['weight']=value
    pck_error_max_gf[dpid1][dpid2]['weight']=1-value

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

def get_gf(option):
    if option == PCK_ERROR_MIN_OPT:
        return pck_error_min_gf
    elif option == PCK_ERROR_MAX_OPT:
        return pck_error_max_gf
    elif option == DELAY_OPT:
        return delay_gf
    elif option == DEFAULT_OPT:
        return grafo

def get_path(ip_int, ip_ext, option):
    return nx.dijkstra_path(get_gf(option), source=ip_int, target=ip_ext, weight='weight')

def add_path_through_gw(ip_int, ip_ext, option,isDpid=False):
    newPath=get_path(ip_int,hosts[0].ip,option)
    h = [host.ip == ip_int for host in hosts ]
    oldPath;
    if option == PCK_ERROR_OPT:
        oldPath = h.isConnected(ip_ext)
        if oldPath is False:
            #add path as it's the first time:
            for i in range (1, len(newPath) - 2):
                #install fluxes from ip_src to ip_dst
                msg = of.ofp_flow_mod()
                msg.priority = __DEFAULT_IP_PATH
                msg.match.nw_dst = IPAddr(str(ip_dst))
                msg.match.nw_proto = 17 # UDP
                msg.match.dl_type = 0x800 #ip
                pt_next_hop = switch[sw_list[i]].dpid_port[sw_list[i+1]]
                msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
                core.openflow.sendToDPID(sw_list[i], msg) #switch i-esimo
            #the reverse
            for i in range (2, len(newPath) - 1):
                #install fluxes from ip_dst to ip_src
                msg = of.ofp_flow_mod()
                msg.priority = __DEFAULT_IP_PATH
                msg.match.nw_dst = IPAddr(str(ip_src))
                msg.match.dl_type = 0x800 #ip
                msg.match.nw_proto = 17 #UDP
                pt_pre_hop = switch[sw_list[i]].dpid_port[sw_list[i-1]]
                msg.actions.append(of.ofp_action_output(port = pt_pre_hop ))
                core.openflow.sendToDPID(sw_list[i], msg) #switch i-esimo
            h.addConnection(hosts[0],path,UDP)
        else:
            for i in range(2,max(len(oldPath,newPath))-2):
                if oldPath[i-1] == newPath[i-1]: #same switch
                    if oldPath[i] == newPath[i]: # also the same next hop
                        if oldPath[i+1] == newPath[i+1]:
                            continue
                        else: # the i+1 switch is different

                            msg = of.ofp_flow_mod()
                            msg.command = of.OFPFC_MODIFY
                            msg.match.nw_dst = IPAddr(str(ip_dst))
                            msg.match.nw_proto = 17 # UDP
                            msg.priority = __DEFAULT_IP_PATH
                            msg.match.dl_type = 0x800 #ip
                            pt_next_hop = switch[newPath[i-1]].dpid_port[newPath[i]]
                            msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
                            core.openflow.sendToDPID(newPath[i], msg) #switch i-th
                            #delete previous rules for the other switches
                            for j in range(i,len(oldPath)-1):

                                msg = of.ofp_flow_mod()
                                msg.command = of.OFPFC_DELETE
                                msg.priority = __DEFAULT_IP_PATH
                                msg.match.nw_dst = IPAddr(str(ip_dst))
                                msg.match.nw_proto = 17 # UDP
                                msg.match.dl_type = 0x800 #ip
                                core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                #delete also the reverse path
                                msg = of.ofp_flow_mod()
                                msg.command = of.OFPFC_DELETE
                                msg.priority = __DEFAULT_IP_PATH
                                msg.match.nw_dst = IPAddr(str(ip_src))
                                msg.match.nw_proto = 17 # UDP
                                msg.match.dl_type = 0x800 #ip
                                core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                            #install new rules
                            for j in range (i,len(newPath)-2):
                                msg=of.ofp_flow_mod()

                                msg.priority = __DEFAULT_IP_PATH
                                msg.match.nw_dst = IPAddr(str(ip_dst))
                                msg.match.dl_type = 0x800 #ip
                                pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                                msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                                core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                            h.addConnection(host[0],newPath,UDP)
                            return
                    else:
                        msg = of.ofp_flow_mod()
                        msg.command = of.OFPFC_MODIFY
                        msg.match.nw_dst = IPAddr(str(ip_dst))
                        msg.match.nw_proto = 17 # UDP
                        msg.priority = __DEFAULT_IP_PATH
                        msg.match.dl_type = 0x800 #ip
                        pt_next_hop = switch[newPath[i-1]].dpid_port[newPath[i]]
                        msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
                        core.openflow.sendToDPID(newPath[i], msg) #switch i-th
                        #reverse
                        msg = of.ofp_flow_mod()
                        msg.command = of.OFPFC_MODIFY
                        msg.priority = __DEFAULT_IP_PATH
                        msg.match.nw_dst = IPAddr(str(ip_src))
                        msg.match.nw_proto = 17 # UDP
                        msg.match.dl_type = 0x800 #ip
                        pt_pre_hop = switch[newPath[i]].dpid_port[newPath[i+1]]
                        msg.actions.append(of.ofp_action_output(port = pt_pre_hop ))
                        core.openflow.sendToDPID(newPath[i], msg) #switch i-th



    #devo fare in modo di riconoscere uno switch come gateway
    #capire nella realta' come arrivano i dpid

def add_path(ip_src, ip_dst, option):
    sw_list = nx.dijkstra_path(get_gf(option), source=ip_src, target=ip_dst, weight='weight')
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

def add_default_rules(dpid, net = None):
    """
    add default rules on new switch
    arp request flooding and in/out network traffic
    """
    msg = of.ofp_flow_mod()
    msg.priority = __DEFAULT_RULES_PRIORITY
    msg.match.dl_type = 0x806 #arp reques
    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD ))
    core.openflow.sendToDPID(dpid, msg)

    #msg del delay discovery
    msg = of.ofp_flow_mod()
    msg.priority = 5000
    msg.match.dl_type = 0x800 #ip type
    msg.match.nw_src = IPAddr("100.100.100.1")
    msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER ))
    core.openflow.sendToDPID(dpid, msg)

    # the default rules: if it's in the network, flood. otherwise go through the gateway
    #to reach the internet
    if net is not None:
        _drop_private_IPs(net) # drop all the connections through private IPs that are not in the network
                                # and send PacketIn to controller
        # flood internal network
        msg = of.ofp_flow_mod()
        msg.priority = __DEFAULT_INT_NET_RULE # lowest rule ever
        msg.match.dl_type = 0x800 #ip type
        msg.match.nw_dst = net
        acts = []
        acts.append(of.ofp_action_output(port = of.OFPP_CONTROLLER)) # packetIn
        acts.append(of.ofp_action_output(port=of.OFPP_ALL)) # flood the network
        msg.actions = acts
        core.openflow.sendToDPID(dpid, msg)

        if dpid == hosts[0].switch[0]: # the switch is connected to the NATP router
            sw = switch[dpid] # I have all the characteristics of the switch

            msg = of.ofp_flow_mod()
            # second lowest rule. If this switch is added after others, this rule will overcome
            #the default rule to the gateway
            msg.priority = __DEFAULT_EXT_NET_RULE + 2
            msg.match.dl_type = 0x800 #ip type
            msg.actions.append(of.ofp_action_output(port=host[0].switch[1]))
            core.openflow.sendToDPID(dpid, msg)
        #see if the switch for the internet has been found and this dpid is not connected to the router
        elif host[0].mac == EthAddr("ff:ff:ff:ff:ff:ff"):
            add_path_to_gw(dpid,host[0].ip,DEFAULT_OPT,isDpid=True) # send also the PacketIn

        # send to the packet to the next switch

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
        # self.host_gaming={} # if port has a gaming host, value is True
        # self.heavy_traffic={} # if port has an host who is making a lot of traffic, here is true

    #def add_host(self, mac, porta, ip):
    def add_host(h, port):
        "add host on the switch's port"
        if ( not isinstance(h,Host)):
            raise("h not a member of class host in my_Switch.add_host")

        # if self.dpid_port.has_key(ip):
        #     log.debug("IP still exist on the switch")
        # else:
        #     self.dpid_port[ip] = porta
        #     self.port_dpid[porta] = ip
        #     self.port_mac[porta] = mac
        #     self.mac_port[mac] = porta
        self.port_dpid[port]=h
        msg = of.ofp_flow_mod()
        msg.priority = 100
        msg.match.dl_type = 0x806 #arp reques
        msg.match.dl_dst = EthAddr(str(h.mac))
        msg.actions.append(of.ofp_action_output(port = port ))
        core.openflow.sendToDPID(self.dpid, msg)
        msg = of.ofp_flow_mod()
        msg.priority = 1000
        msg.match.nw_dst = IPAddr(str(h.ip))
        msg.match.dl_type = 0x800 #ip
        msg.actions.append(of.ofp_action_output(port = port ))
        core.openflow.sendToDPID(self.dpid, msg)

class Host():
    TRANSP_BOTH = 0
    TCP=1
    UDP=2
    def __init__(self, dpid,portN, ipAddr=None, macAddr=None ):
        if(ipAddr is not None and not isinstance(ipAddr,IPAddr)):
            raise("Invalid argument. ip address must be an IPAddr object")
        self.isGaming=False
        self.traffic = False
        self.connectedToTCP = {}
        self.connectedToUDP = {}
        self.switch = ( dpid , portN) # tuple for the
        self.ip=ipAddr
        self.mac=macAddr
        self.lastChange = datetime.datetime.now() #current time in seconds
        hosts.append(self) # add itself to the host list

    def setGaming(self,g):
        self.isGaming=g
    def isGaming(self):
        return self.isGaming
    def setTraffic(t):
        self.traffic=t
    def getTraffic():
        return self.traffic

    def addConnection(host,path=None, t_type=TRANSP_BOTH):
        #update timer if ip exist
        if not isinstance(host,Host):
            pass #TODO
        if(t_type == TRANSP_BOTH):
            if path is not None: # add both traffic
                log.debug("adding both transport connection to the host destination")
            else:
                log.debug("adding host to the connected one")
            self.connectedToUDP[host] = (datetime.datetime.now(),path)
            self.connectedToTCP[host] = (datetime.datetime.now(),path)
            self.lastChange = datetime.datetime.now()
        elif t_type == TCP:
            if path is not None: # add both traffic
                log.debug("adding TCP path to the host destination")
                self.lastChange = datetime.datetime.now()
                self.connectedToTCP[host] = (datetime.datetime.now(),path)
            else:
                log.debug("adding host to the connected one")
        elif t_type == UDP:
            if path is not None: # add both traffic
                log.debug("adding UDP path to the host destination")
            else:
                log.debug("adding host to the connected one via UDP")
            self.lastChange = datetime.datetime.now()
            self.connectedToUDP[host] = (datetime.datetime.now(),path)

        else:
            log.error("unknown option given for t_type")


    def isConnected(ip,t_type):
        """if is connected return the time since when it was connected [datetime.datetime] and
        the path to that IP or Host
        otherwise return False"""
        if isinstance(ip,IPAddr):
            for host,value in self.connectedToUDP:
                if ip == host.ip and not t_type == TCP: # e' un ip e sono in UDP o entrambe
                    return value
            for host,value in self.connectedToTCP:
                if ip == host.ip and not t_type == UDP:
                    return value
            return False

        elif isinstance(ip,Host):
            for host,value in self.connectedToUDP:
                if ip.ip == host.ip and not t_type == TCP: # e' un ip e sono in UDP o entrambe
                    return value
            for host,value in self.connectedToTCP:
                if ip.ip == host.ip and not t_type == UDP:
                    return value
            return False


    def cleanExpiredIp():
        for p, conn in enumerate(self.connectedToTCP):
            if((conn[1]+IP_TIMEOUT)>datetime.datetime.now()):
                del connectedToTCP[p] # remove the tuple

        for p, conn in enumerate(self.connectedToUDP):
            if((conn[1]+IP_TIMEOUT)>datetime.datetime.now()):
                del connectedToUDP[p] # remove the tuple

def ipCleaner():
    for h in hosts:
        h.cleanExpiredIp()
