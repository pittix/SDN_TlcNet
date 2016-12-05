"""This class is a modification of the pox.openflow.discovery
it is based on the paper Efficient Topology Discovery in software
defined networks by F. Pakzad & others (available on the IEEE explore website)
it Extends the class Discovery and modifies the packet sent, such that the cpu
load is lowered more than 30% in the controller.Moreover the network usage is
smaller as the number of ofp_packet_out is one per switch, instead one per port
of each switch. See DOI: 10.1109/ICSPCS.2014.7021050  """

import pox.openflow.discovery as Disc

class Discovery(Disc):
    """docstring for Discovery.Disc  """
    def __init__(self, arg):
        super(Discovery,Disc.__init__()
        self.arg = arg

    def _handle_openflow_ConnectionUp(self,event):
        links= [link for link in self.adjacency
                if link.dpid1 == event.dpid
                or link.dpid2 == event.dpid ]
        super._handle_openflow_ConnectionUp(self,event)

        return links

    def _handle_openflow_PacketIn(self,event):
        """
        Retrieve the relation (switch_K,port_J)<->(switch_N,port_L)
        The return dictionary has the following data:
        'sourceMac' : source mac of the switch sending the LLDP packet
        'sourceID' : the destination switch  number identifier
        'dstMac' : the destination mac of the receiver sw3itch
        'dstID' : the destination switch number identifier
        """
        switch_discovered={}
        pkt=event.parsed #get layer 2 packet

        if (pkt.effective_ethertype != pkt.ethernet.LLDP_TYPE
            or pkt.dst != pkt.ethernet.ETHERNET.NDP_MULTICAST):
            return

        lldpHead=pkt.find(pkt.lldp)
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
        switch_discovered["srcMac"]= pkt.src # get source mac (LL src)
        switch_discovered["srcID"]=int(lldpHead.tlvs[0].id[5:],16)
        switch_discovered["dstMac"]=pkt.dst #destination mac (LL dst)
        switch_discovered["dstID"]= event.dpid
        return switch_discovered
