#!/usr/bin/python
import time
import my_topo_SDN as myTopo
import StatsHandler as SH
from pox.lib.recoco import Timer  #for recoursive functions
UPD_GRAPH = 10 # every 10 seconds update the graph weight
