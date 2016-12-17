from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
import time
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente

dpid = list()
DESC_STATS = 1
FLOW_STATS = 2
TABLE_STATS = 4
PORT_STATS = 8
QUEUE_STATS = 16
AGGREGATE_STATS=None
def req_stats(dpid, type=DESC_STATS, port=1, tab=1):
    """
    Evaluates the request to be done
    """
    con=core.openflow.getConnection(dpid)
    if type is None: #default do the aggregate
        con.send(of.ofp_stats_request(body=of.ofp_aggregate_stats_request()))
    if ((type & DESC_STATS) != 0) :
        con.send(of.ofp_stats_request(body=of.ofp_desc_stats_request()))
    if ((type & FLOW_STATS) != 0) :
        con.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
    if ((type & TABLE_STATS) != 0) :
        con.send(of.ofp_stats_request(body=of.ofp_table_stats_request()))#table=tab)))
    if ((type & PORT_STATS) != 0) :
        con.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))#port = port)))
    if ((type & QUEUE_STATS) != 0) :
        con.send(of.ofp_stats_request(body=of.ofp_queue_stats_request()))#port=port)))

def _handle_flow_stats(event):
    stat_flow = event.stats
    print ("FLOW_STATS: %s",stat_flow)
    #return None #todo
def _handle_port_stats(event):
    stat_port = event.stats
    print ("PORT_STATS: %s",stat_port)
    #return None #todo

def req_connectionToHost(host):
    return None
def _handle_queue_stats(event):
    stat_queue = event.stats
    print ("Queue_STATS: %s",stat_queue)
    #return None
def _handle_table_stats(event):
    stat_tab = event.stats
    print ("Table_STATS: %s",stat_tab)
    #return None
def _handle_aggregate_stats(event):
    stat_aggr = event.stats
    print ("Aggregate_STATS: %s",stat_aggr)
    #return None
def _handle_desc_stats(event):
    stat_desc = event.stats
    print ("Description_STATS: %s",stat_desc)
def launch():
    core.openflow.addListenerByName("FlowStatsReceived", _handle_flow_stats)
    core.openflow.addListenerByName("SwitchDescReceived", _handle_desc_stats)
    core.openflow.addListenerByName("QueueStatsReceived", _handle_queue_stats)
    core.openflow.addListenerByName("PortStatsReceived", _handle_port_stats)
    core.openflow.addListenerByName("TableStatsReceived", _handle_table_stats)
    # core.openflow.addListenerByName("AggregateStatsReceived", _handle_aggregate_stats)
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnUp)
    Timer(5, _create_stat_request, recurring=True) #every 2 seconds execute _show_topo


def _create_stat_request():
    for typ in [1,2,4,8,16,None]:
        for sw in dpid:
            req_stats(sw, type=typ, port = 1, tab=1)
def _handle_ConnUp(event):
    dpid.append(event.dpid)
#
# class DescStats():
#     self.port={}
#     self.table={}
#     self.queue={}
#     self.flow={}
#     self.switch={}
#     def __init__():
#         self.port
