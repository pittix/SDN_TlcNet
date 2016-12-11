#classe topo SDN
#che utilizzo nel mio controller
# e' un oggetti in fine
from pox.core import core
from pox.lib.util import dpid_to_str

import networkx as nx            #libreria per i grafi
import matplotlib.pyplot as plt  #libreria matlab per plottare i grafi

log = core.getLogger()

class topo():
    def __init__(self):
        self.switch = {} #dizionario di switch dpid e' la chiave
        self.grafo = nx.Graph()
        self.ip_to_switch = {} #dizionario in cui l'ip solo le chiavi e i valori gli switch

    def add_host(self, dpid, mac, port, ip):
        """
        add host on the graph and the port of switch
        """
        #devo aggiungere le porte allo switch
        #da finire
        x = True
        try:
            self.ip_to_switch[dpid_to_str(dpid)] = ip
        except:
            log.debug("Add host to switch that don't exist")
            x = False
        if x: #se lo switch e' presente
            self.switch[dpid].add_host(mac, port, ip)
            self.grafo.add_node(ip)
            self.grafo.add_edge(dpid, ip)

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
        log.debug("saved image graph")
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


class my_Switch():
    def __init__(self, dpid):
        self.dpid = dpid
        self.dpid_port = {}  #chiave dpid/ip valore porta
        self.port_dpid = {}
        self.port_mac = {}
        self.mac_port = {}

    def add_host(self, mac, port, ip):
        "add host on the switch's port"
        try:
            port = self.dpid_port[ip]
            log.debug("IP still exist on the switch")
        except:
            self.dpid_port[ip] = port
            self.port_dpid[port] = ip
            self.port_mac[port] = mac
            self.mac_port[mac] = port
