import my_topo_SDN as topo
import my_controller
import stats_handler as sh
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr

def checkChanges():
    for h in topo.hosts:
        if h.gaming: # redirect tcp through the least delay
            for dstH,path in h.connectedTo:
                sw_list = nx.dijkstra_path(get_gf(DELAY_OPT), source=h.ip, target=dstH.ip, weight='weight')
