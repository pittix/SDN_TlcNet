#classe topo SDN
#che utilizzo nel mio controller
# e' un oggetti in fine
from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr

import networkx as nx            #libreria per i grafi
import matplotlib.pyplot as plt  #libreria matlab per plottare i grafi

log = core.getLogger()

class topo():
    def __init__(self):
        self.switch = {} #dizionario di switch dpid e' la chiave
        self.grafo = nx.Graph()
        self.ip_to_switch = {} #dizionario in cui l'ip solo le chiavi e i valori gli elementi switch
        self.mac_to_ip = {} #per gli host

    def add_host(self, dpid, mac, port, ip):
        """
        add host on the graph and the port of switch
        """
        #devo aggiungere le porte allo switch
        #da finire
        x = True
        try:
            self.switch[dpid]
        except:
            log.debug("Add host to switch that don't exist")
            x = False
        if x: #se lo switch e' presente
            self.switch[dpid].add_host(mac, port, ip)
            self.mac_to_ip[mac] = ip
            self.ip_to_switch[ip] = self.switch[dpid]
            self.grafo.add_node(ip)
            self.grafo.add_edge(dpid, ip)
            log.debug("add host %s", ip)


    def add_switch(self, dpid):
        """
        aggiungo uno switch se non e' gia' presente
        """
        if self.switch.has_key(dpid):
            pass
        else:
            log.debug("switch non presente da aggiungere")
            sw = my_Switch(dpid)
            self.switch[dpid] = sw
            self.grafo.add_node(dpid)

        msg = of.ofp_flow_mod()
        msg.priority = 50
        msg.match.dl_type = 0x806 #arp reques
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD ))
        core.openflow.sendToDPID(dpid, msg)


    def rm_switch(self, dpid):
        """
        se e' presente elimina lo switch
        """
        x = True
        try:
            self.grafo.remove_node(dpid)
            del self.switch[dpid]
        except:
            x = False
        if x:
            #elimina i link sui nodi che a lui erano collegati se possibile
            pass

    def save_graph(self):
        nx.draw_networkx(self.grafo)          #stampa anche il grafo
        plt.savefig("grafo.png")         #salva l'immagine
        #log.debug("saved image graph")
        plt.clf()                        #elimina l'immagine corrente dalla libreria

        #key = self.switch.keys()
        #for i in range (0, len(key)):
        #    print self.switch[key[i]].dpid

    def add_link(self, dpid1, port1, dpid2, port2):
        self.add_switch(dpid1)
        self.add_switch(dpid2)

        self.switch[dpid1].port_dpid[port1] = dpid2
        self.switch[dpid1].dpid_port[dpid2] = port1

        self.switch[dpid2].port_dpid[port2] = dpid1
        self.switch[dpid2].dpid_port[dpid1] = port2

        self.grafo.add_edge(dpid1, dpid2)

    def rm_link(self, dpid1, port1, dpid2, port2):
        x = True
        try:
            self.grafo.remove_edge(dpid1, dpid2)
        except:
            #se tento di rimuovere un link che non e' presente nel grafo
            x = False
        if x:
            del self.switch[dpid1].port_dpid[port1]
            del self.switch[dpid1].dpid_port[dpid2]

            del self.switch[dpid2].port_dpid[port2]
            del self.switch[dpid2].dpid_port[dpid1]

    def add_default_path(self, ip_src, ip_dst):
        sw_list = nx.shortest_path(self.grafo,source=ip_src, target=ip_dst)
        log.debug(sw_list)
        for i in range (1, len(sw_list) - 2):
            #installo i flussi da ip_src a ip_dst

            msg = of.ofp_flow_mod()
            msg.priority = 1001
            msg.match.nw_dst = IPAddr(str(ip_dst))
            msg.match.dl_type = 0x800 #ip
            pt_next_hope = self.switch[sw_list[i]].dpid_port[sw_list[i+1]]
            msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
            core.openflow.sendToDPID(sw_list[i], msg) #switch i-esimo
            #print("primo ciclo for %i porta %s", i, pt_next_hope)
            msg = of.ofp_flow_mod()
            msg.priority = 150
            msg.match.dl_type = 0x806 #arp reques
            #msg.match.dl_dst = EthAddr(str(mac))
            msg.match.nw_dst = IPAddr(str(ip_dst))
            msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
            core.openflow.sendToDPID(sw_list[i], msg)

        for i in range (2, len(sw_list) - 1):
            #installo i flussi da ip_dst a ip_src

            msg = of.ofp_flow_mod()
            msg.priority = 1001
            msg.match.nw_dst = IPAddr(str(ip_src))
            msg.match.dl_type = 0x800 #ip
            pt_pre_hope = self.switch[sw_list[i]].dpid_port[sw_list[i-1]]
            msg.actions.append(of.ofp_action_output(port = pt_pre_hope ))
            core.openflow.sendToDPID(sw_list[i], msg) #switch i-esimo
            #print("secondo ciclo for %i porta %s", i, pt_pre_hope)
            msg = of.ofp_flow_mod()
            msg.priority = 150
            msg.match.dl_type = 0x806 #arp reques
            #msg.match.dl_dst = EthAddr(str(mac))
            msg.match.nw_dst = IPAddr(str(ip_src))
            msg.actions.append(of.ofp_action_output(port = pt_pre_hope ))
            core.openflow.sendToDPID(sw_list[i], msg)



    def ip_connected(self, ip1, ip2):
        x = True
        #log.debug("ip_connected ip1 %s ip2 %s", str(ip1), str(ip2))
        try:
            self.ip_to_switch[ip1]
        except:
            #log.debug("ip1 not found")
            x = False

        try:
            self.ip_to_switch[ip2]
        except:
            #log.debug("ip2 not found")
            x = False

        if x:
            if nx.has_path(self.grafo, source=ip1, target=ip2):
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

    def add_host(self, mac, porta, ip):
        "add host on the switch's port"
        try:
            pt = self.dpid_port[ip]
            log.debug("IP still exist on the switch")
        except:
            self.dpid_port[ip] = porta
            self.port_dpid[porta] = ip
            self.port_mac[porta] = mac
            self.mac_port[mac] = porta
            log.debug("aggiungo host %s e installare regole", ip)

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
