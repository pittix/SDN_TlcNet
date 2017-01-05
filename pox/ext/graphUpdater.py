#!/usr/bin/python
import time
import my_topo_SDN as myTopo
import StatsHandler as SH

class GraphUpdater:
    def __init__(self):
        Timer(UPD_GRAPH, GraphUpdater._updateGraph,recurring = True)
        self.handling = SH() #start the timer where gets the stats
    def _updateGraph():
        for switch in myTopo.switch:
            _setPktLoss(handlig.getStats(SH.StatsType.PORT,dpid),dpid)

    def _setPktLoss(stat,dpid):
        """
        From each dpid gets the number of packets transmitted and how many of them were
        corrupted. Then puts the weight on the graph edge
        """
        if stat is None:
        pErrRate=list()
        return; # there is no stat
        for port in stat:
            errors=port["rxDropped"]+port["txDropped"]+port["rxErr"]+port["txErr"]
            total = port["txPkt"]+port["rxPkt"] #total packet transmission
            pErrRate.append(errors/total)
        #get the link connection for a switch/port and update the weight
        for i,PER in enumerate(pErrRate):
            dpid2=myTopo.switch[dpid].port_dpid[i+1] # get the dpid connected to that port
            myTopo.link_pathloss(dpid,dpid2,PER) # Update the packet error rate

    def _setLinkLoad(stat,dpid):
        """
        consider the load as how much te node queue is filled.
        more it's filled, worse is the weight
        """
        if stat is None: return #no stats available

        for portN,queue in enumerate(stats):
            dpid2=myTopo.switch[dpid].port_dpid[portN]
            mytopo.link_load(dpid, dpid2, queue["txE"]) # if the queue is full, packets will be dropped
