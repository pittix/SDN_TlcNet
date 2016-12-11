"""
find the topology of the network. Uses the second version of the OFDP proposed
in DOI:10.1109/ICSPCS.2014.7021050 (available in the IEEE explorer website)
"""
from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.openflow.switches import *
from pox.lib.revent import *
log=core.getLogger()
class findTopology(Event):
    sw=Switches()

    def _handle_ConnectionUp(self,event):
        """
        For the connectionUp event add the switch to the graph and
        """
            #ask for feature to this new switch
        feature_request(event.dpid)
        self.event=event #save connection

            #handle feature reply packet arrival (FeatureRes event)
    def _handle_FeatureRes(self,event):
        #recheck if it's a feature reply packet
        packet=event.parsed            ## WRONG, I think
        match = of.ofp_match.from_packet(packet)
        if match.type != of.OFPT_FEATURES_REPLY: ##CHECK if WRONG
            return #not my packet
        portsInfo=packet.phy_port #PhyPort vector. @see flowgrammable
        # Extract mac address for each port. I can extract also the state (connected, link down, listening)
        ports=Port()

        for p in portsInfo:
            #convention used with matteo, the i port is in the i-1 position in the vector
            #in the port number I put inside the mac address
            ports.addPort(p.id,p.hw_addr,p.state,p.feature)
            # ports[p.id.in_port -1] = p.state

        #add the switch to the graph
        sw.addSwitch(event.dpid, ports)

        #FeatureReq event generator
    def feature_request(swID):
        """create a new openflow packet for the switch indicated in swID to ask for
        its ports and their state
        """
        msg=of.ofp_feature_request()
        core.openflow.sendToDPID(swID, msg) #Send Feature request
    def launch():
        #topo=findTopology()
        #core.registerNew(findTopology,"my_topo")
        core.openflow.addListenerByName("FeatureRes",_handle_FeatureRes)
        core.openflow.addListenerByName("ConnectionUp",_handle_ConnectionUp)
