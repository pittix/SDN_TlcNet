from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, IPAddr6, EthAddr
import time
from pox.lib.recoco import Timer  #per eseguire funzioni ricorsivamente
import my_topo_SDN as myTopo
import pox.lib.packet as pkt
from datetime import datetime
import ipaddress
import random
import multiprocessing #multiprocess
import my_topo_SDN as topo #new class

log = core.getLogger()

lista = {} #lista dpid rtt

def init_lista():
    ls = topo.switch.keys() #lista chiavi dpid della my topo
    for i in range (0, len(ls)):
        lista[ls[i]] = my_rtt(ls[i]) #assegno un oggetto rtt ad ogni dpid

    #log.debug(lista)

def get_rtt():
    """deve aggiornare tutti gli rtt"""
    key = lista.keys() #lista dei dpid degli switch
    for switch in key:
        send_msg(switch)

def send_msg(dpid):
    #mando un msg a quel dpid e setto i nomi sul suo oggetto rtt
    #create a msg
    ip_dst = "100.%d.%d.%d" % (random.randint(0,250),random.randint(0,250), random.randint(0,250)) #docro' crearlo univoco
    identity = IPAddr(ip_dst)
    msg = create_msg(ipdst = ip_dst)
    core.openflow.sendToDPID(dpid, msg)
    lista[dpid].add_rtt(identity)


def create_msg(ipsrc = "100.100.100.0", ipdst = "100.100.100.1", mac_src = "80:80:80:80:80:80", mac_dst = "50:50:50:50:50:50", port = of.OFPP_CONTROLLER):
    ipv4_pck = pkt.ipv4()
    ipv4_pck.srcip = IPAddr(ipsrc)
    ipv4_pck.dstip = IPAddr(ipdst)
    ether = pkt.ethernet()
    ether.type = pkt.ethernet.IP_TYPE
    ether.dst = mac_dst
    ether.src = mac_src
    ether.payload = ipv4_pck
    msg = of.ofp_packet_out()
    msg.data = ether.pack()
    msg.actions.append(of.ofp_action_output(port = port))
    return msg


def _handle_PacketIn(event):
    time = datetime.now()
    packet = event.parsed
    if packet.type == packet.IP_TYPE:
        ip_packet = packet.find('ipv4')
        ip_dst = ip_packet.dstip #ip destinatario

        if ipaddress.IPv4Address(ip_packet.srcip) == ipaddress.IPv4Address('100.100.100.0'):
            lista[event.dpid].update_rtt(ip_dst, time)
            lista[event.dpid].calcolate_rtt(ip_dst)
            #log.debug("\n\n %s", ip_dst)
            log.debug("\n\ndpid= %s rtt %s", event.dpid, lista[event.dpid].av_rtt)


def verify_list_consistence():
    #controlla se la mia lista di switch e' aggiornata con quella della topo
    pass
    # if mia lista != lista my_topo:
    #     update_switch_list()

def update_switch_list():
    #aggiorna la mia lista come quella su my_topo
    pass

class my_rtt():
    def __init__(self, dpid):
        self.av_rtt = -1 #rtt medio
        self.temp_rtt = {}  #chiave int identificativo del preciso rtt value list of start and end

    def add_rtt(self, ide):
        self.temp_rtt[ide]  = [datetime.now(), -1, -1] #start, end, rtt in ms

    def update_rtt(self, ide, time):
        self.temp_rtt[ide][1] = time
        c = (((self.temp_rtt[ide][1]) - (self.temp_rtt[ide][0])).microseconds)/1000
        self.temp_rtt[ide][2] = c


    def calcolate_rtt(self, ip_dst):
        #per ora metto l'unico rtt che ho nel rtt medio ma poi posso fare la media
        #rtt_list =  #lista di tutti gli rtt che ho
        #if (self.temp_rtt[rtt_list[0]][2] != -1): # se nel primo elemento c'e' un rtt valido
        rtt = self.av_rtt + self.temp_rtt[ip_dst][2]
        self.av_rtt =  rtt/len(self.temp_rtt.keys())

        log.debug("nessun Rtt valido da poter inserire")

def launch():
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    Timer(7, init_lista, recurring=False) #inizializza la lista e il programma
    #Timer(2, verify_list_consistence, recurring=True) #every 2 seconds execute _show_topo
    Timer(5, get_rtt, recurring=True) #aggiorna tutti gli rtt
