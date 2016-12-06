from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
import pox.lib.packet as pkt #per analizzare i pacchetti
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()


s0_dpid=0
s1_dpid=0
s2_dpid=0

flusso_UDP = 0 #se e' a zero non c'e' flusso UDP se e' a uno e' presente

def _handle_ConnectionUp (event):
	global s0_dpid, s1_dpid, s2_dpid
	global flusso_UDP
	print "ConnectionUp: ", dpidToStr(event.connection.dpid)

	#remember the connection dpid for switch
	for m in event.connection.features.ports:
		if m.name == "s0-eth1":
			s0_dpid = event.connection.dpid
			print "s0_dpid=", s0_dpid
		elif m.name == "s1-eth1":
			s1_dpid = event.connection.dpid
			print "s1_dpid=", s1_dpid
		elif m.name == "s2-eth1":
			s2_dpid = event.connection.dpid
			print "s2_dpid=", s2_dpid


def _handle_PacketIn (event):
	global s0_dpid, s1_dpid, s2_dpid
	global flusso_UDP
	print "PacketIn: ", dpidToStr(event.connection.dpid) #stampa il mac a video 
	packet = event.parsed # This is the parsed packet data.
	if not packet.parsed:
		print "Ignoring incomplete packet"
		return
	flusso_UDP = 0
	packet_in = event.ofp # The actual ofp_packet_in message.
	
#	inport = event.port	#porta dello switch da cui proviene il pacchetto
#	src_mac = packet.src	#mac del sorgente del pacchetto
#	dst_mac = packet.dst	#mac del destinatario del pacchetto 
	
	ipv4_packet = packet.find('ipv4') #
	icmp_packet = packet.find('icmp') # serve per come ho usato i metodi dentro agli switch

	print "ciao pinoooooooooooooooooooooooooooooooo"
#	if ipv4_packet:
#		src_ip = ipv4_packet.srcip
#		dst_ip = ipv4_packet.dstip
#		print "ip_src", src_ip 
#		print "ip_dst", dst_ip
	
	if event.connection.dpid==s0_dpid: 	#il pacchetto stato spedito dallo switch s0
			
		if packet.type == packet.ARP_TYPE:	#analisi pacchetti ARP
			print "arp packet received nello switch s0"	
			msg = of.ofp_packet_out()
			msg.data = packet_in
		 	if msg.in_port == 1:		#se e stato ricevuto dalla porta uno rimandalo sulla porta due
				action = of.ofp_action_output(port = 3)	
					
			elif msg.in_port == 3:		#se e stato ricevuto sulla porta 1 mandalo sulla porta due
				action = of.ofp_action_output(port = 1)

			msg.actions.append(action) 	#inoltra il pacchetto di tipo arp 
			event.connection.send(msg)

			#installa il flusso arp 
			msg = of.ofp_flow_mod()
			msg.priority = 100	
			msg.match.in_port = 1
			msg.match.dl_type = 0x806 #arp reques
			msg.actions.append(of.ofp_action_output(port = 3))
			event.connection.send(msg)

			msg = of.ofp_flow_mod()
			msg.priority = 100	
			msg.match.in_port = 3
			msg.match.dl_type = 0x806 #arp reques
			msg.actions.append(of.ofp_action_output(port = 1))
			event.connection.send(msg)

		elif packet.type == packet.IP_TYPE:
			ip_packet = packet.payload
			if ip_packet.protocol == 1: #messaggio ICMP
				msg = of.ofp_packet_out()
				msg.data = packet_in
				if ip_packet.dstip == IPAddr("192.168.1.3"):
					action = of.ofp_action_output(port = 1)	
				elif ip_packet.dstip == IPAddr("192.168.1.2"):
					action = of.ofp_action_output(port = 3)	

				elif ip_packet.dstip == IPAddr("192.168.1.1"):
					action = of.ofp_action_output(port = 3)
				msg.actions.append(action)
				event.connection.send(msg)

				#installa i flussi ICMP
				msg = of.ofp_flow_mod() 		#ICMP request
				msg.priority = 100	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.3"
				msg.match.nw_proto = 1 #ICMPv4 request
				msg.actions.append(of.ofp_action_output(port = 1))
				event.connection.send(msg)
		
				msg = of.ofp_flow_mod() 		#ICMP request
				msg.priority = 100	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.2"
				msg.match.nw_proto = 1 #ICMPv4 request
				msg.actions.append(of.ofp_action_output(port = 3))
				event.connection.send(msg)

				msg = of.ofp_flow_mod() 		#ICMP request
				msg.priority = 100	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.1"
				msg.match.nw_proto = 1 #ICMPv4 request
				msg.actions.append(of.ofp_action_output(port = 3))
				event.connection.send(msg)

			elif ip_packet.protocol == 6: #messaggio TCP inserire dei temporizzatori per mettere le decisioni 
				msg = of.ofp_packet_out()
				msg.data = packet_in
				if ip_packet.dstip == IPAddr("192.168.1.3"):
					action = of.ofp_action_output(port = 1)	

				elif ip_packet.dstip == IPAddr("192.168.1.2"):
					action = of.ofp_action_output(port = 3)	

				elif ip_packet.dstip == IPAddr("192.168.1.1"):
					action = of.ofp_action_output(port = 3)
				msg.actions.append(action)
				event.connection.send(msg)
		
				msg = of.ofp_flow_mod() 		#TCP
				msg.priority = 1000	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.1"
				msg.match.nw_proto = 6 #TCP
				msg.idle_timeout = 1   #se per due secondi non ci sono pacchetti elimina la regola
    				#msg.hard_timeout = 2   #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 3))
				event.connection.send(msg)
						
				msg = of.ofp_flow_mod() 		#TCP
				msg.priority = 1000	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.2"
				msg.match.nw_proto = 6 #TCP
				msg.idle_timeout = 1   #se per due secondi non ci sono pacchetti elimina la regola
    				#msg.hard_timeout = 2   #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 2))
				event.connection.send(msg)
				
				msg = of.ofp_flow_mod() 		#ANY
				msg.priority = 1000
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.3"
				msg.idle_timeout = 1   #se per due secondi non ci sono pacchetti elimina la regola
    				#msg.hard_timeout = 2   #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 1))
				event.connection.send(msg)

				
			elif ip_packet.protocol == 17: #messaggio UDP
				print "pacchetto UDP arrivato"
				flusso_UDP = 1 #indica che e' presente un flusso UDP 

				msg = of.ofp_flow_mod() 		#UDP
				msg.priority = 1000
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.1"
				msg.match.nw_proto = 17 #UDP
				msg.idle_timeout = 1  #se per due secondi non ci sono pacchetti elimina la regola
    				msg.hard_timeout = 1   #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 2))
				event.connection.send(msg)

				#sovrascrivi gli altri TCP che passano per sopra forse posso unire tutti i TCP senza specificiare dst
				msg = of.ofp_flow_mod() 		#TCP
				msg.priority = 1000	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.1"
				msg.match.nw_proto = 6 #TCP
				msg.idle_timeout = 1   #se per due secondi non ci sono pacchetti elimina la regola
    				msg.hard_timeout = 1  #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 3))
				event.connection.send(msg)

				msg = of.ofp_flow_mod() 		#TCP
				msg.priority = 1000	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.2"
				msg.match.nw_proto = 6 #TCP
				msg.idle_timeout = 1    #se per due secondi non ci sono pacchetti elimina la regola
    				msg.hard_timeout = 1   #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 3))
				event.connection.send(msg)

				msg = of.ofp_flow_mod() 		#ANY
				msg.priority = 1000	
				msg.match.dl_type = 0x800 #Livello 3
				msg.match.nw_dst = "192.168.1.3"
				msg.idle_timeout = 1    #se per due secondi non ci sono pacchetti elimina la regola
    				msg.hard_timeout = 2   #in ogni caso elimina la regola dopo 15 secondi 
				msg.actions.append(of.ofp_action_output(port = 1))
				event.connection.send(msg)


	elif event.connection.dpid==s1_dpid:

		print "switch s1"
		msg = of.ofp_packet_out()
		msg.data = packet_in
		#qui devo semplicemente mettere un flusso fisso da dirgli appena si connette oltre ad inoltrare il pacchetto 	
		if msg.in_port == 1:		#se e stato ricevuto dalla porta uno rimandalo sulla porta due
			action = of.ofp_action_output(port = 2)	
		elif msg.in_port == 2:		#se e stato ricevuto sulla porta 1 mandalo sulla porta due
			action = of.ofp_action_output(port = 1)

		msg.actions.append(action) 	#aggiung l'azione da fare
		event.connection.send(msg)

		msg = of.ofp_flow_mod()
		msg.priority =100
		msg.match.in_port = 1
		msg.actions.append(of.ofp_action_output(port = 2))
		event.connection.send(msg)
	
		msg = of.ofp_flow_mod()
		msg.priority =100
		msg.match.in_port = 2
		msg.actions.append(of.ofp_action_output(port = 1))
		event.connection.send(msg)

		

	elif event.connection.dpid==s2_dpid:
		
		if packet.type == packet.ARP_TYPE:
			msg = of.ofp_packet_out()	#IN QUESTO MODO I PACCHETTI ARP PASSANO TUTTI DI QUI
			msg.data = packet_in
			if msg.in_port == 2:		#se e stato ricevuto dalla porta uno rimandalo sulla porta due
				msg.actions.append(of.ofp_action_output(port = 3))  
				msg.actions.append(of.ofp_action_output(port = 4))

			elif msg.in_port == 3:		#se e stato ricevuto sulla porta 3 mandalo sulla porta due
				msg.actions.append(of.ofp_action_output(port = 2))  
				msg.actions.append(of.ofp_action_output(port = 4))

			elif msg.in_port == 4:		#se e stato ricevuto sulla porta 4 mandalo sulla porta due
				msg.actions.append(of.ofp_action_output(port = 2))  
				msg.actions.append(of.ofp_action_output(port = 3))

			event.connection.send(msg)

			#installo tutti i flussi 
			msg = of.ofp_flow_mod()
			msg.priority =100
			msg.match.in_port = 2
			msg.match.dl_type = 0x806
			msg.actions.append(of.ofp_action_output(port = 3))  
			msg.actions.append(of.ofp_action_output(port = 4))
			event.connection.send(msg)
	
			msg = of.ofp_flow_mod()
			msg.priority = 100
			msg.match.in_port = 3
			msg.match.dl_type = 0x806
			msg.actions.append(of.ofp_action_output(port = 2))
			msg.actions.append(of.ofp_action_output(port = 4))
			event.connection.send(msg)
	
			msg = of.ofp_flow_mod()
			msg.priority =100
			msg.match.in_port = 4
			msg.match.dl_type = 0x806
			msg.actions.append(of.ofp_action_output(port = 2))
			msg.actions.append(of.ofp_action_output(port = 3))
			event.connection.send(msg)	

		elif packet.type == packet.IP_TYPE:
			
			msg = of.ofp_flow_mod() 		#ANY
			msg.priority = 1000		
			msg.match.dl_type = 0x800 #Livello 3
			msg.match.nw_dst = "192.168.1.1"
			msg.actions.append(of.ofp_action_output(port = 3))
			event.connection.send(msg)
	
			msg = of.ofp_flow_mod() 		#ANY
			msg.priority = 1000		
			msg.match.dl_type = 0x800 #Livello 3
			msg.match.nw_dst = "192.168.1.2"
			msg.actions.append(of.ofp_action_output(port = 4))
			event.connection.send(msg)
	
			msg = of.ofp_flow_mod() 		#ANY
			msg.priority = 1000		
			msg.match.dl_type = 0x800 #Livello 3
			msg.match.nw_dst = "192.168.1.3"
			msg.actions.append(of.ofp_action_output(port = 2))
			event.connection.send(msg)

		
def launch ():
	core.openflow.addListenerByName("ConnectionUp",_handle_ConnectionUp)
	core.openflow.addListenerByName("PacketIn",_handle_PacketIn)
