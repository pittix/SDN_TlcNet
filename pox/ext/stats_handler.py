from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
import time
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente
import my_topo_SDN as myTopo;
log = core.getLogger()

dpid = list()
DESC_STATS = 1
FLOW_STATS = 2
TABLE_STATS = 4
PORT_STATS = 8
QUEUE_STATS = 16
AGGREGATE_STATS=None
UPD_GRAPH = 10 # every 10 seconds update the graph weight
# class can be executed by pox core
def launch():
    core.openflow.addListenerByName("FlowStatsReceived", _handle_flow_stats)
    core.openflow.addListenerByName("SwitchDescReceived", _handle_desc_stats)
    core.openflow.addListenerByName("QueueStatsReceived", _handle_queue_stats)
    core.openflow.addListenerByName("PortStatsReceived", _handle_port_stats)
    core.openflow.addListenerByName("TableStatsReceived", _handle_table_stats)
    # core.openflow.addListenerByName("AggregateStatsReceived", _handle_aggregate_stats)
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnUp)
    Timer(5, _create_stat_request, recurring=True) #every 5 seconds execute _show_topo

def _create_stat_request():
    for typ in [6 , 24]: # 2 stats per switch at every cycle
        for sw in dpid:
            req_stats(sw, type=typ)#, port = 1, tab=1) I want all stats
            time.sleep(0.1) #don't fill the network with stats packets

def _handle_ConnUp(event):
    dpid.append(event.dpid)


def req_stats(dpid, type=DESC_STATS, port=1, tab=1):
    """
    Evaluates the request to be done
    """
    con=core.openflow.getConnection(dpid)
    if type is None: #default do the aggregate
        con.send(of.ofp_stats_request(body=of.ofp_aggregate_stats_request()))
        return
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
    #stat_flow = event.stats
    flow_dict=[]
    for i,rule in enumerate(event.stats):
        flow_dict.append({})
        flow_dict[i-1]["tableID"] = rule.table_id
        #flow_dict[i-1]["pad"] = rule.pad
        flow_dict[i-1]["match"] = rule.match.show()
        flow_dict[i-1]["Tsecond"] = rule.duration_sec
        flow_dict[i-1]["Tnanos"] = rule.duration_nsec
        flow_dict[i-1]["Pri"] = rule.priority
        flow_dict[i-1]["HardTimeout"] = rule.hard_timeout
        flow_dict[i-1]["IdleTimeout"] = rule.idle_timeout
        flow_dict[i-1]["cookie"] = rule.cookie
        flow_dict[i-1]["pktCount"] = rule.packet_count
        flow_dict[i-1]["byteCount"] = rule.byte_count
        flow_dict[i-1]["actions"] = []
        # for j,act in enumerate(rule.actions):
        #     flow_dict[i-1]["actions"][j-1] = {}
        #     flow_dict[i-1]["actions"][j-1][""] =
    # print ("FLOW_STATS")
    # print(flow_dict)
    StatsHandler.__saveStats(StatsType.FLOW, event.dpid, flow_dict)

    #print(stat_flow)
    #return None #todo
def _handle_port_stats(event):
    # stat_port = event.stats
    port_dict=[]
    for i,port in enumerate(event.stats):
        port_dict.append({})
        port_dict[i-1]["Pnum"] = port.port_no
        port_dict[i-1]["rxPkts"] = port.rx_packets
        port_dict[i-1]["txPkts"] = port.tx_packets
        port_dict[i-1]["rxB"] = port.rx_bytes
        port_dict[i-1]["txB"]= port.tx_bytes
        port_dict[i-1]["rxDropped"] = port.rx_dropped
        port_dict[i-1]["txDropped"]= port.tx_dropped
        port_dict[i-1]["rxErr"] = port.rx_errors
        port_dict[i-1]["txErr"] = port.tx_errors
        port_dict[i-1]["rxFrameErr"] = port.rx_frame_err
        port_dict[i-1]["rxOverErr"] = port.rx_over_err
        port_dict[i-1]["crcErr"] = port.rx_crc_err
        port_dict[i-1]["collision"] = port.collisions
    #print ("PORT_STATS")
    #print(stat_port)
    StatsHandler.__saveStats(StatsType.PORT, event.dpid, port_dict)

    #print(port_dict)
    #return None #todo

# def req_connectionToHost(host):
#     return None
def _handle_queue_stats(event):
    #stat_queue = event.stats
    queue_dict=[]
    for i,port in enumerate(event.stats): #stats for each port' queue
        queue_dict.append({})
        queue_dict[i-1]["Pnum"] = port.port_no
        queue_dict[i-1]["length"] = port.queue_id
        queue_dict[i-1]["txB"] = port.tx_bytes
        queue_dict[i-1]["txPkts"] = port.tx_packets
        queue_dict[i-1]["txE"] = port.tx_errors
    #print ("Queue_STATS")
    StatsHandler.__saveStats(StatsType.QUEUE, event.dpid, queue_dict)

    #return queue_dict
    #print(stat_queue)
    #return None
def _handle_table_stats(event):
    # stat_tab = event.stats
    tab_dict=[]
    for i,tab in enumerate(event.stats): #extract all tables
        tab_dict.append({})
        tab_dict[i-1]["table_id"] = tab.table_id
        tab_dict[i-1]["name"] = tab.name
        tab_dict[i-1]["wildcards"] = tab.wildcards
        tab_dict[i-1]["maxEntries"] = tab.max_entries
        tab_dict[i-1]["activeCount"] = tab.active_count
        tab_dict[i-1]["lookupCount"] = tab.lookup_count
        tab_dict[i-1]["matched"] = tab.matched_count
    #print ("Table_STATS")
    StatsHandler.__saveStats(StatsType.TABLE, event.dpid, tab_dict)
    #return None
def _handle_aggregate_stats(event):
    stat_aggr = event.stats
    aggr_dict={}
    aggr_dict["pktCount"] = stat_aggr.packet_count
    aggr_dict["byteCount"] = stat_aggr.byte_count
    aggr_dict["flowCount"] = stat_aggr.flow_count
    #aggr_dict["pad"] = stat_aggr.pad
    #print ("Aggregate_STATS")
    #return aggr_dict;
    #return None
def _handle_desc_stats(event): ###WORKING
    stat_desc = event.stats
    desc_dict={}
    desc_dict["hw"]=stat_desc.hw_desc
    desc_dict["sw"]=stat_desc.sw_desc
    desc_dict["mfr"]=stat_desc.mfr_desc
    desc_dict["SN"]=stat_desc.serial_num
    desc_dict["dp"]=stat_desc.dp_desc
    #print ("Description_STATS:")
    return desc_dict

class StatsHandler:
stats = list(4) # create the stats
    def __saveStats(sType,dpid, stats):
        if not (dpid in stats[sType]):
            stats[sType].update({dpid:""}) # add the dpid dictionary
            stats[sType][dpid]= {} #create the space to save the stat in this
        stats[sType][dpid]=stats # overwrite the stats
        log.debug("added the stats for dpid %i",dpid)

    def getStats(self,sType, dpid, port=None, table=None,flow=None):
        """ Try to get the stats for the specified dpid. If no stats is found, return None
        """
        if sType is None:
            raise ValueError("type cannot be None, use a type from StatsType")
        if dpid is None:
            raise ValueError("dpid cannot be None, use a valid dpid")

        if sType == StatsType.PORT:
            return __getPortStat(dpid,port)
        if sType == StatsType.TABLE:
            return __getTableStat(dpid,table)
        if sType == StatsType.QUEUE:
            return __getQueueStat(dpid,port)
        if sType == StatsType.FLOW:
            return __getQueueStat(dpid,flow)
        # should never reach there
        else
            raise ValueError("stats type was not recognized, please choose one from StatsType")

    def __getQueueStat(dpid, port):
        if not dpid in stats[StatsType.QUEUE]: # check if I have some stats for this dpid
            return None;
        if port is None: # check if all stats are needed
            return stats[StatsType.QUEUE][dpid] # list of dictionary
        if not port in stats[StatsType.QUEUE][dpid]: # if no stats is available for that port
            return None
        return stats[StatsType.QUEUE][dpid][port-1] # dictionary with stats of that port

    def __getTableStat(dpid,table):
        if not dpid in stats[StatsType.TABLE]: # check if I have some stats for this dpid
            return None;
        if table is None: # check if all stats are needed
            return stats[StatsType.TABLE][dpid] # list of dictionary
        if not table in stats[StatsType.TABLE][dpid]: # if no stats is available for that port
            return None
        return stats[StatsType.TABLE][dpid][table-1] # dictionary with stats of that port

    def __getPortStat(dpid, port=None):
        """
        Get the statistic about one or all port of a specific switch
        indicated in the dpid. The return type is a dictionary (if only one port
        has been specified. otherwise a list of dictionary) with those keys:
        Pnum = port number; txB, rxB the number of bytes sent or received in that port
        txP, rxP the number of packet sent or received on the port,
        txE, rxE the number
        of error occoured in transmission;
        txDroped, rxDropped the number of packet dropped because of the queue
        crcErr the number of errors encountered during crc checks
        collision the number of collision happened

        if no port is specified, the list has the port# in the port#-1 position of the list.

        if no stats is available for this couple, return None
        """
        if not dpid in stats[StatsType.PORT]:
            return None;
        if port is None:
            return stats[StatsType.PORT][dpid] # list of dictionary
        if not port in stats[StatsType.PORT][dpid]:
            return None
        return stats[StatsType.PORT][dpid][port-1] # dictionary

    def __getFlowStat(dpid,flow):
        if not dpid in stats[StatsType.FLOW]:
            return None;
        if flow is None:
            return stats[StatsType.FLOW][dpid] # list of dictionary
        if not port in stats[StatsType.FLOW][dpid]:
            return None
        return stats[StatsType.FLOW][dpid][flow-1] # dictionary



class StatsType(Enum):
    PORT=1
    TABLE=2
    #FLOW=3
    QUEUE=0
