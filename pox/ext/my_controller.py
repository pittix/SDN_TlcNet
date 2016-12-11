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

by Matteo Maso & Andrea Pittaro
"""
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
import pox.topology
from pox.openflow.discovery import Discovery
import pox.openflow.topology
from pox.lib.util import dpid_to_str
#import pox.host_tracker
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente

import time
import multiprocessing #multiprocess
import networkx as nx            #libreria per i grafi
import matplotlib.pyplot as plt  #libreria matlab per plottare i grafi
import findTopology
log = core.getLogger()

grafo = nx.Graph()

switch = {} #dizionario di switch dpid e' la chiave

class my_Switch():
    def __init__(self, dpid):
        self.dpid = dpid
        self.dpid_port = {}  #chiave dpid valore porta
        self.port_dpid = {}
        self.port_mac = {}
        self.mac_port = {}

def my_add_switch(dpid):
    """
    aggiungo uno switch se non e' gia' presente
    """
    if switch.has_key(dpid):
        pass
    else:
        log.debug("switch non presente da aggiungere")
        sw = my_Switch(dpid)
        switch[dpid] = sw
        grafo.add_node(dpid)

def my_rm_switch(dpid):
    """
    se e' presente elimina lo switch
    """
    x = True
    try:
        grafo.remove_node(dpid)
        del switch[dpid]
    except:
        x = False
    if x:
        #elimina i link sui nodi che a lui erano collegati se possibile
        pass

def my_add_link(dpid1, port1, dpid2, port2):
    my_add_switch(dpid1)
    my_add_switch(dpid2)

    switch[dpid1].port_dpid[port1] = dpid2
    switch[dpid1].dpid_port[dpid2] = port1

    switch[dpid2].port_dpid[port2] = dpid1
    switch[dpid2].dpid_port[dpid1] = port2

    grafo.add_edge(dpid1, dpid2)

def my_rm_link(dpid1, port1, dpid2, port2):
    x = True
    try:
        grafo.remove_edge(dpid1, dpid2)
    except:
        #se tento di rimuovere un link che non e' presente nel grafo
        x = False
    if x:
        del switch[dpid1].port_dpid[port1]
        del switch[dpid1].dpid_port[dpid2]

        del switch[dpid2].port_dpid[port2]
        del switch[dpid2].dpid_port[dpid1]


def _handle_LinkEvent(event):
    """
    acquisisce gli eventi di tipo LinkEvent della classe openflow.discovery
    """
    l = event.link
    if event.added:
        log.debug('LinkAdd dpid1: {0} porta {1}, dpid2: {2} porta {3}'.format(l.dpid1, l.port1, l.dpid2, l.port2))
        my_add_link(l.dpid1, l.port1, l.dpid2, l.port2)
    elif event.removed:
        log.debug('LinkRemoved dpid1: {0} porta {1}, dpid2: {2} porta {3}'.format(l.dpid1, l.port1, l.dpid2, l.port2))
        my_rm_link(l.dpid1, l.port1, l.dpid2, l.port2)
    else:
        pass


def save_graph():
    nx.draw_networkx(grafo)          #stampa anche il grafo
    plt.savefig("grafo.png")         #salva l'immagine
    log.debug("saved image graph")
    plt.clf()                        #elimina l'immagine corrente dalla libreria


def _show_topo():
    """
    function to show the graph on a separate process

    funzione da sistemare, il multirocesso in questo caso non e' necessario

    """
    job_for_another_core = multiprocessing.Process(target=save_graph,args=()) #chiama la funzione save_graph in un processo separato
    job_for_another_core.start()

    key = switch.keys()
    for i in range (0, len(key)):
        a=3
        #print switch[key[i]].dpid
    #log.debug("thread mostra grafo matteeeeoooooooooooo")

def launch():
    """
    start:
        pox.topology.launch()
        pox.openflow.discovery.launch()
        pox.openflow.topology.launch()
        findTopology()
    and make listeners functions
    """
    pox.topology.launch()
    pox.openflow.discovery.launch()
    pox.openflow.topology.launch()
    core.openflow_discovery.addListenerByName("LinkEvent", _handle_LinkEvent)
    Timer(2, _show_topo, recurring=True) #every 2 seconds execute _show_topo

#def launch ():
    #pox.topology.launch()
    #pox.openflow.discovery.launch()
    #pox.openflow.topology.launch()
    #pox.host_tracker.launch()
    #import pox.topo_graph
    #pox.topo_graph.launch()
    #core.openflow_discovery.addListenerByName("LinkEvent", _handle_LinkEvent)
