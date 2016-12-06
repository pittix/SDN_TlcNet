"""
find the topology of the network. Uses the second version of the OFDP proposed
in DOI:10.1109/ICSPCS.2014.7021050 (available in the IEEE explorer website)
"""
from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt

class findTopology(self)
self.net=Network();

    def _handle_ConnectionUp(self,event):
        """
        For the connectionUp event add the switch to the graph and
        """
            #ask for feature to this new switch
            feature_request(event.dpid)
            net.add_switch(dpid)
            self.event=event #save connection

            #handle feature reply packet arrival (FeatureRes event)
    def _handle_FeatureRes(self,event):
        #recheck if it's a feature reply packet
        packet=event.parsed            ## WRONG, I think
        match = of.ofp_match.from_packet(packet)
        if match.type != of.OFPT_FEATURES_REPLY ##CHECK if WRONG
            return #not my packet
        portsInfo=packet.phy_port #PhyPort vector. @see flowgrammable
        # Extract mac address for each port. I can extract also the state (connected, link down, listening)
        for p in portsInfo:
            #convention used with matteo, the i port is in the i-1 position in the vector
            #in the port number I put inside the mac address
            ports[p.id -1]=p.hw_addr
            # ports[p.id.in_port -1] = p.state

        #add the switch to the graph
        net.addSwitch(event.dpid, ports)

        #FeatureReq event generator
    def feature_request(swID):
        """create a new openflow packet for the switch indicated in swID to ask for
        its ports and their state
        """
        msg=of.ofp_feature_request(swID)

        self.connection.send(msg)

    def link_update(**links):

class Discovery(Event)
    __init__(self):
    self.net=Network()

    def send_LLDP(*switches):
        for switch in switches:
            #output to all ports
            msg=of.ofp_packet_out(action = of.ofp_action_output(port=of.OFPP_ALL)))
            msg.data=self.create_LLDP(switch, TTL_TLV);
            self.event.connection.send(msg)

        log.debug("sent all LLDP packets to the switches")


    def create_LLDP(dpid, ttl):
        #put inside the dpid to recognize the packet when it will be received
        chassis_id = pkt.chassis_id(subtype=pkt.chassis_id.SUB_LOCAL)
        chassis_id.id = bytes('dpid:' + hex(long(dpid))[2:-1])
        #as before
        sysdesc = pkt.system_description()
        sysdesc.payload = bytes('dpid:' + hex(long(dpid))[2:-1])
        #create the lldp packet
        discovery_packet = pkt.lldp()
        discovery_packet.tlvs.append(chassis_id)
        discovery_packet.tlvs.append(0) #the controller will check after
        discovery_packet.tlvs.append(ttl)
        discovery_packet.tlvs.append(sysdesc)
        discovery_packet.tlvs.append(pkt.end_tlv())
        eth = pkt.ethernet(type=pkt.ethernet.LLDP_TYPE)
        eth.dst = pkt.ETHERNET.NDP_MULTICAST
        eth.payload = discovery_packet
        return eth.pack()

    def lldp_input_packet(self,event):
        packet=event.parsed
        if (packet.effective_ethertype != pkt.ethernet.LLDP_TYPE
            or pkt.dst != pkt.ethernet.ETHERNET.NDP_MULTICAST):
            return

        lldpHead=packet.find(pkt.lldp)
        if lldpHead is None or not lldpHead.parsed :
            log.error("not a correct LLDP packet")
            return EventHalt
        if len(lldpHead.tlvs)<3
            log.error("LLDP packet doesn't carry enough information ")
            return EventHalt
          return EventHalt
        if lldpHead.tlvs[0].tlv_type != pkt.lldp.CHASSIS_ID_TLV:
          log.error("LLDP packet TLV 1 not CHASSIS_ID")
          return EventHalt
        if lldpHead.tlvs[1].tlv_type != pkt.lldp.PORT_ID_TLV:
          log.error("LLDP packet TLV 2 not PORT_ID")
          return EventHalt
        if lldpHead.tlvs[2].tlv_type != pkt.lldp.TTL_TLV:
          log.error("LLDP packet TLV 3 not TTL")
          return EventHalt
        #allow the code to retrieve how two switches are connected
        switch_discovered["srcMac"]= packet.src # get source mac (LL src)
        switch_discovered["srcID"]=int(lldpHead.tlvs[0].id[5:],16)
        switch_discovered["dstPort"]=packet.port #destination port. Destination mac is multicast
        switch_discovered["dstID"]= event.dpid
        return switch_discovered
