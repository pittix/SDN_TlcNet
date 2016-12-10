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
#import pox.host_tracker
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente

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

def _show_topo():
    """
    function to show the graph on a separate process

    funzione da sistemare, il multirocesso in questo caso non e' necessario

    """
    job_for_another_core = multiprocessing.Process(target=topo.save_graph,args=()) #chiama la funzione save_graph in un processo separato
    job_for_another_core.start()

    #log.debug("thread mostra grafo matteeeeoooooooooooo")

def launch():
    """
    start:
        pox.topology.launch()
        pox.openflow.discovery.launch()
        pox.openflow.topology.launch()

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
