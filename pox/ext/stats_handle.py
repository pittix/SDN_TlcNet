from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
import time
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente
import my_topo_SDN as myTopo
log = core.getLogger()
from enum import Enum

stats = list() # create the stats
stats.append({})
stats.append({})
stats.append({})
stats.append({})
# def saluta():
#     log.debug("\n\n ciao ciao \n\n")

PORT=1
TABLE=2
FLOW=3
QUEUE=0

def _saveStats(sType,dpid, new_stats):
    if not (dpid in stats[sType]):
        stats[sType].update({dpid:""}) # add the dpid dictionary
        stats[sType][dpid]= {} #create the space to save the stat in this

    stats[sType][dpid]=new_stats # overwrite the stats
    log.debug("added the stats for dpid %i",dpid)

def getStats(sType, dpid, port=None, table=None,flow=None):
    """ Try to get the stats for the specified dpid. If no stats is found, return None
    """
    if sType is None:
        raise ValueError("type cannot be None, use a type from StatsType")
    if dpid is None:
        raise ValueError("dpid cannot be None, use a valid dpid")

    if sType == PORT:
        return _getPortStat(dpid,port)
    if sType == TABLE:
        return _getTableStat(dpid,table)
    if sType == QUEUE:
        return _getQueueStat(dpid,port)
    if sType == FLOW:
        return _getQueueStat(dpid,flow)
    # should never reach there
    else:
            raise ValueError("stats type was not recognized, please choose one from StatsType")

def _getQueueStat(dpid, port):
    if not dpid in stats[StatsType.QUEUE]: # check if I have some stats for this dpid
        return None;
    if port is None: # check if all stats are needed
        return stats[StatsType.QUEUE][dpid] # list of dictionary
    if not port in stats[StatsType.QUEUE][dpid]: # if no stats is available for that port
        return None
    return stats[StatsType.QUEUE][dpid][port-1] # dictionary with stats of that port

def _getTableStat(dpid,table):
    if not dpid in stats[StatsType.TABLE]: # check if I have some stats for this dpid
        return None;
    if table is None: # check if all stats are needed
        return stats[StatsType.TABLE][dpid] # list of dictionary
    if not table in stats[StatsType.TABLE][dpid]: # if no stats is available for that port
        return None
    return stats[StatsType.TABLE][dpid][table-1] # dictionary with stats of that port

def _getPortStat(dpid, port=None):
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
    if not (dpid in stats[PORT]):
        return None;
    if port is None:
        return stats[PORT][dpid] # list of dictionary
    if not port in stats[PORT][dpid]:
        return None
    return stats[PORT][dpid][port-1] # dictionary

def _getFlowStat(dpid,flow):
    if not dpid in stats[FLOW]:
        return None;
    if flow is None:
        return stats[FLOW][dpid] # list of dictionary
    if not port in stats[FLOW][dpid]:
        return None
    return stats[FLOW][dpid][flow-1] # dictionary
