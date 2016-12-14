from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of

class Statsistics()
    DESC_STATS = 1
    FLOW_STATS = 2
    TABLE_STATS = 4
    PORT_STATS = 8
    QUEUE_STATS = 16
    AGGREGATE_STATS=None
    def _handle_stats(self,event):

    def req_stats(dpid, type=DESC_STATS):
        """
        Evaluates the request to be done
        """
        con=core.openflow.getConnection(dpid)
        if type is None: #default do the aggregate
            con.send(of.ofp_stats_request(body=of.ofp_aggregate_stats_request()))
        if type & DESC_STATS:
            con.send(of.ofp_stats_request(body=of.ofp_desc_stats_request()))
        if type & FLOW_STATS:
            con.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
        if type & TABLE_STATS:
            con.send(of.ofp_stats_request(body=of.ofp_table_stats_request()))
        if type & PORT_STATS:
            con.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
        if type & QUEUE_STATS:
            con.send(of.ofp_stats_request(body=of.ofp_queue_stats_request()))

    def _handle_flow_stats(self,event):
        self.stat = event.stats

        return None #todo
    def _handle_port_stats(self,event):

    def req_connectionToHost(host):
        return None
    def _handle_queue_stats(self_event):
        return None
    def _handle_table_stats(self,event):
        return None
    def _handle_aggregate_stats(self,event):
        return None
def launch():
    pox.forwarding.l2_learning.launch()
    pox.forwarding.l3_learning.launch()
    core.openflow.addListenerByName("FlowStatsReceived",_handle_flow_stats)
    core.openflow.addListenerByName("SwitchDescReceived",_handle_desc_stats)
    core.openflow.addListenerByName("QueueStatsReceived",_handle_queue_stats)
    core.openflow.addListenerByName("PortStatsReceived",_handle_port_stats)
    core.openflow.addListenerByName("TableStatsReceived",_handle_table_stats)
    core.openflow.addListenerByName("AggregateStatsReceived",_handle_aggregate_stats)

class DescStats():
    self.port={}
    self.table={}
    self.queue={}
    self.flow={}
    self.switch={}
