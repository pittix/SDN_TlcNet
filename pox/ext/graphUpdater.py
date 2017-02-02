import my_topo_SDN as topo
import my_controller
import stats_handler as sh
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr

def checkChanges():
    for h in topo.hosts:
        if h.isGaming: # redirect tcp through the least delay
            for i,val in enumerate(h.connectedToTCP):
                oldPath=h.connectedToTCP[h.connectedToTCP[val]][1]
                if isinstance(oldPath,datetime.datetime):
                    continue
                dstH=val
                newPath = nx.dijkstra_path(get_gf(DELAY_OPT), source=h.ip, target=dstH.ip, weight='weight')
                if len(oldPath)!= len(newPath):
                    change_path(oldPath,newPath,topo.TCP)
                    h.addConnection(dstH,newPath)
                else:
                    for i in range (1,len(oldPath)):
                        if(oldPath[i]==newPath[i]):
                            continue
                        else:
                            change_path(oldPath,newPath,topo.TCP)
                            h.addConnection(dstH,newPath)
            for i,val in enumerate(h.connectedToUDP):
                oldPath=h.connectedToUDP[h.connectedToUDP[val]][1]
                if isinstance(oldPath,datetime.datetime):
                    continue
                dstH=val
                newPath = nx.dijkstra_path(get_gf(DELAY_OPT), source=h.ip, target=dstH.ip, weight='weight')
                if len(oldPath)!= len(newPath):
                    change_path(oldPath,newPath,topo.UDP)
                    h.addConnection(dstH,newPath)
                else:
                    for i in range (1,len(oldPath)):
                        if(oldPath[i]==newPath[i]):
                            continue
                        else:
                            change_path(oldPath,newPath,topo.UDP)
                            h.addConnection(dstH,newPath)

        elif h.traffic:
            for i,val in enumerate(h.connectedToUDP):
                oldPath=h.connectedToUDP[h.connectedToUDP[val]][1]
                dstH=val
                if isinstance(oldPath,datetime.datetime):
                    continue
                newPath = nx.dijkstra_path(get_gf(PCK_ERROR_MAX_OPT), source=h.ip, target=dstH.ip, weight='weight')
                if len(oldPath)!= len(newPath):
                    change_path(oldPath,newPath,topo.UDP)
                    h.addConnection(dstH,newPath)
                else:
                    for i in range (1,len(oldPath)):
                        if(oldPath[i]==newPath[i]):
                            continue
                        else:
                            change_path(oldPath,newPath,topo.UDP)
                            h.addConnection(dstH,newPath)

        else: # default rule
            for i,val in enumerate(h.connectedToTCP):
                oldPath=h.connectedToTCP[h.connectedToTCP[val]][1]
                if isinstance(oldPath,datetime.datetime):
                    continue
                dstH=val
                newPath = nx.dijkstra_path(get_gf(PCK_ERROR_MIN_OPT), source=h.ip, target=dstH.ip, weight='weight')
                if len(oldPath)!= len(newPath):
                    change_path(oldPath,newPath,topo.TCP)
                    h.addConnection(dstH,newPath)
                else:
                    for i in range (1,len(oldPath)):
                        if(oldPath[i]==newPath[i]):
                            continue
                        else:
                            change_path(oldPath,newPath,topo.TCP)
                            h.addConnection(dstH,newPath)


def change_path(oldPath,newPath,opt):
    if opt == topo.TCP:
        for i in range(1,max(len(oldPath,newPath))-2): # first two rules are the same (Host obj and swtich)
            if oldPath[i-1] == newPath[i-1]: #same switch
                if oldPath[i] == newPath[i]: # also the same next hop
                    if oldPath[i+1] == newPath[i+1]:
                        continue
                    else: # the i+1 switch is different

                        msg = of.ofp_flow_mod()
                        msg.command = of.OFPFC_MODIFY
                        msg.match.nw_dst = IPAddr(str(ip_dst))
                        msg.match.nw_src = IPAddr(str(ip_src))
                        msg.match.nw_proto = 6 # TCP
                        msg.priority = __DEFAULT_IP_PATH
                        msg.match.dl_type = 0x800 #ip
                        pt_next_hop = switch[newPath[i-1]].dpid_port[newPath[i]]
                        msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
                        core.openflow.sendToDPID(newPath[i], msg) #switch i-th
                        #delete previous rules for the other switches

                        for j in range(i,len(oldPath)-1):
                            msg = of.ofp_flow_mod()
                            msg.command = of.OFPFC_DELETE
                            msg.priority = __DEFAULT_IP_PATH
                            msg.match.nw_dst = IPAddr(str(ip_dst))
                            msg.match.nw_src = IPAddr(str(ip_src))
                            msg.match.nw_proto = 17 # UDP
                            msg.match.dl_type = 0x800 #ip
                            core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                            #delete also the reverse path
                            msg = of.ofp_flow_mod()
                            msg.command = of.OFPFC_DELETE
                            msg.priority = __DEFAULT_IP_PATH
                            msg.match.nw_dst = IPAddr(str(ip_src))
                            msg.match.nw_src = IPAddr(str(ip_dst))
                            msg.match.nw_proto = 6 # TCP
                            msg.match.dl_type = 0x800 #ip
                            core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                        #install new rules
                        for j in range (i,len(newPath)-2):
                            msg=of.ofp_flow_mod()

                            msg.priority = __DEFAULT_IP_PATH
                            msg.match.nw_dst = IPAddr(str(ip_dst))
                            msg.match.nw_src = IPAddr(str(ip_src))
                            msg.match.dl_type = 0x800 #ip
                            pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                            msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                            core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                        h.addConnection(ip_ext,newPath,UDP)
                        return
                else:
                    #TODO cancella e reinstalla
                    for j in range(i,len(oldPath)-1):
                        msg = of.ofp_flow_mod()
                        msg.command = of.OFPFC_DELETE
                        msg.priority = __DEFAULT_IP_PATH
                        msg.match.nw_dst = IPAddr(str(ip_dst))
                        msg.match.nw_src = IPAddr(str(ip_src))
                        msg.match.nw_proto = 6 # TCP
                        msg.match.dl_type = 0x800 #ip
                        core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                        #delete also the reverse path
                        msg = of.ofp_flow_mod()
                        msg.command = of.OFPFC_DELETE
                        msg.priority = __DEFAULT_IP_PATH
                        msg.match.nw_dst = IPAddr(str(ip_src))
                        msg.match.nw_src = IPAddr(str(ip_dst))
                        msg.match.nw_proto = 6 # TCP
                        msg.match.dl_type = 0x800 #ip
                        core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                    #install new rules
                    for j in range (i,len(newPath)-2):
                        msg=of.ofp_flow_mod()

                        msg.priority = __DEFAULT_IP_PATH
                        msg.match.nw_dst = IPAddr(str(ip_dst))
                        msg.match.nw_src = IPAddr(str(ip_src))
                        msg.match.dl_type = 0x800 #ip
                        msg.match.nw_proto = 6 #TCP
                        pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                        msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                        core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
            else:
                log.error("S_i-1 and S_i-1' should always be the same")
    elif opt == topo.UDP:
        for i in range (1, len(newPath) - 2):
            #install fluxes from ip_src to ip_dst
            msg = of.ofp_flow_mod()
            msg.priority = __DEFAULT_IP_PATH
            msg.match.nw_dst = IPAddr(str(ip_dst))
            msg.match.nw_src = IPAddr(str(ip_src))
            msg.match.nw_proto = 17 # UDP
            msg.match.dl_type = 0x800 #ip
            pt_next_hop = switch[newPath[i]].dpid_port[newPath[i+1]] #TODO
            msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
            core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
            #the reverse
            for i in range (2, len(newPath) - 1):
                #install fluxes from ip_dst to ip_src
                msg = of.ofp_flow_mod()
                msg.priority = __DEFAULT_IP_PATH
                msg.match.nw_dst = IPAddr(str(ip_src))
                msg.match.nw_src = IPAddr(str(ip_dst))
                msg.match.dl_type = 0x800 #ip
                msg.match.nw_proto = 17 #UDP
                pt_pre_hop = switch[newPath[i]].dpid_port[newPath[i-1]] #TODO
                msg.actions.append(of.ofp_action_output(port = pt_pre_hop ))
                core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                h.addConnection(hosts[0],path,UDP)
            else:
                for i in range(1,max(len(oldPath,newPath))-2): # first two rules are the same (Host obj and swtich)
                    if oldPath[i-1] == newPath[i-1]: #same switch
                        if oldPath[i] == newPath[i]: # also the same next hop
                            if oldPath[i+1] == newPath[i+1]:
                                continue
                            else: # the i+1 switch is different

                                msg = of.ofp_flow_mod()
                                msg.command = of.OFPFC_MODIFY
                                msg.match.nw_dst = IPAddr(str(ip_dst))
                                msg.match.nw_src = IPAddr(str(ip_src))
                                msg.match.nw_proto = 17 # UDP
                                msg.priority = __DEFAULT_IP_PATH
                                msg.match.dl_type = 0x800 #ip
                                pt_next_hop = switch[newPath[i-1]].dpid_port[newPath[i]]
                                msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
                                core.openflow.sendToDPID(newPath[i], msg) #switch i-th
                                #delete previous rules for the other switches

                                for j in range(i,len(oldPath)-1):
                                    msg = of.ofp_flow_mod()
                                    msg.command = of.OFPFC_DELETE
                                    msg.priority = __DEFAULT_IP_PATH
                                    msg.match.nw_dst = IPAddr(str(ip_dst))
                                    msg.match.nw_src = IPAddr(str(ip_src))
                                    msg.match.nw_proto = 17 # UDP
                                    msg.match.dl_type = 0x800 #ip
                                    core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                    #delete also the reverse path
                                    msg = of.ofp_flow_mod()
                                    msg.command = of.OFPFC_DELETE
                                    msg.priority = __DEFAULT_IP_PATH
                                    msg.match.nw_dst = IPAddr(str(ip_src))
                                    msg.match.nw_src = IPAddr(str(ip_dst))
                                    msg.match.nw_proto = 17 # UDP
                                    msg.match.dl_type = 0x800 #ip
                                    core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                    #install new rules
                                    for j in range (i,len(newPath)-2):
                                        msg=of.ofp_flow_mod()

                                        msg.priority = __DEFAULT_IP_PATH
                                        msg.match.nw_dst = IPAddr(str(ip_dst))
                                        msg.match.nw_src = IPAddr(str(ip_src))
                                        msg.match.dl_type = 0x800 #ip
                                        pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                                        msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                                        core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                                        h.addConnection(ip_ext,newPath,UDP)
                                        return
                                    else:
                                        #TODO cancella e reinstalla
                                        for j in range(i,len(oldPath)-1):
                                            msg = of.ofp_flow_mod()
                                            msg.command = of.OFPFC_DELETE
                                            msg.priority = __DEFAULT_IP_PATH
                                            msg.match.nw_dst = IPAddr(str(ip_dst))
                                            msg.match.nw_src = IPAddr(str(ip_src))
                                            msg.match.nw_proto = 17 # UDP
                                            msg.match.dl_type = 0x800 #ip
                                            core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                            #delete also the reverse path
                                            msg = of.ofp_flow_mod()
                                            msg.command = of.OFPFC_DELETE
                                            msg.priority = __DEFAULT_IP_PATH
                                            msg.match.nw_dst = IPAddr(str(ip_src))
                                            msg.match.nw_src = IPAddr(str(ip_dst))
                                            msg.match.nw_proto = 17 # UDP
                                            msg.match.dl_type = 0x800 #ip
                                            core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                            #install new rules
                                            for j in range (i,len(newPath)-2):
                                                msg=of.ofp_flow_mod()

                                                msg.priority = __DEFAULT_IP_PATH
                                                msg.match.nw_dst = IPAddr(str(ip_dst))
                                                msg.match.nw_src = IPAddr(str(ip_src))
                                                msg.match.dl_type = 0x800 #ip
                                                msg.match.nw_proto = 17 # UDP
                                                pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                                                msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                                                core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                        else:
                            log.error("S_i-1 and S_i-1' should always be the same")
    else:
        for i in range (1, len(newPath) - 2):
            #install fluxes from ip_src to ip_dst
            msg = of.ofp_flow_mod()
            msg.priority = __DEFAULT_IP_PATH
            msg.match.nw_dst = IPAddr(str(ip_dst))
            msg.match.nw_src = IPAddr(str(ip_src))
            msg.match.dl_type = 0x800 #ip
            pt_next_hop = switch[newPath[i]].dpid_port[newPath[i+1]] #TODO
            msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
            core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
            #the reverse
            for i in range (2, len(newPath) - 1):
                #install fluxes from ip_dst to ip_src
                msg = of.ofp_flow_mod()
                msg.priority = __DEFAULT_IP_PATH
                msg.match.nw_dst = IPAddr(str(ip_src))
                msg.match.nw_src = IPAddr(str(ip_dst))
                msg.match.dl_type = 0x800 #ip
                pt_pre_hop = switch[newPath[i]].dpid_port[newPath[i-1]] #TODO
                msg.actions.append(of.ofp_action_output(port = pt_pre_hop ))
                core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                h.addConnection(hosts[0],path,UDP)
            else:
                for i in range(1,max(len(oldPath,newPath))-2): # first two rules are the same (Host obj and swtich)
                    if oldPath[i-1] == newPath[i-1]: #same switch
                        if oldPath[i] == newPath[i]: # also the same next hop
                            if oldPath[i+1] == newPath[i+1]:
                                continue
                            else: # the i+1 switch is different

                                msg = of.ofp_flow_mod()
                                msg.command = of.OFPFC_MODIFY
                                msg.match.nw_dst = IPAddr(str(ip_dst))
                                msg.match.nw_src = IPAddr(str(ip_src))
                                msg.priority = __DEFAULT_IP_PATH
                                msg.match.dl_type = 0x800 #ip
                                pt_next_hop = switch[newPath[i-1]].dpid_port[newPath[i]]
                                msg.actions.append(of.ofp_action_output(port = pt_next_hop ))
                                core.openflow.sendToDPID(newPath[i], msg) #switch i-th
                                #delete previous rules for the other switches

                                for j in range(i,len(oldPath)-1):
                                    msg = of.ofp_flow_mod()
                                    msg.command = of.OFPFC_DELETE
                                    msg.priority = __DEFAULT_IP_PATH
                                    msg.match.nw_dst = IPAddr(str(ip_dst))
                                    msg.match.nw_src = IPAddr(str(ip_src))
                                    msg.match.dl_type = 0x800 #ip
                                    core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                    #delete also the reverse path
                                    msg = of.ofp_flow_mod()
                                    msg.command = of.OFPFC_DELETE
                                    msg.priority = __DEFAULT_IP_PATH
                                    msg.match.nw_dst = IPAddr(str(ip_src))
                                    msg.match.nw_src = IPAddr(str(ip_dst))
                                    msg.match.dl_type = 0x800 #ip
                                    core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                    #install new rules
                                    for j in range (i,len(newPath)-2):
                                        msg=of.ofp_flow_mod()

                                        msg.priority = __DEFAULT_IP_PATH
                                        msg.match.nw_dst = IPAddr(str(ip_dst))
                                        msg.match.nw_src = IPAddr(str(ip_src))
                                        msg.match.dl_type = 0x800 #ip
                                        pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                                        msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                                        core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                                        h.addConnection(ip_ext,newPath,UDP)
                                        return
                                    else:
                                        #TODO cancella e reinstalla
                                        for j in range(i,len(oldPath)-1):
                                            msg = of.ofp_flow_mod()
                                            msg.command = of.OFPFC_DELETE
                                            msg.priority = __DEFAULT_IP_PATH
                                            msg.match.nw_dst = IPAddr(str(ip_dst))
                                            msg.match.nw_src = IPAddr(str(ip_src))
                                            msg.match.dl_type = 0x800 #ip
                                            core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                            #delete also the reverse path
                                            msg = of.ofp_flow_mod()
                                            msg.command = of.OFPFC_DELETE
                                            msg.priority = __DEFAULT_IP_PATH
                                            msg.match.nw_dst = IPAddr(str(ip_src))
                                            msg.match.nw_src = IPAddr(str(ip_dst))
                                            msg.match.dl_type = 0x800 #ip
                                            core.openflow.sendToDPID(oldPath[j+1], msg) #switch i-th
                                            #install new rules
                                            for j in range (i,len(newPath)-2):
                                                msg=of.ofp_flow_mod()

                                                msg.priority = __DEFAULT_IP_PATH
                                                msg.match.nw_dst = IPAddr(str(ip_dst))
                                                msg.match.nw_src = IPAddr(str(ip_src))
                                                msg.match.dl_type = 0x800 #ip
                                                pt_next_hope = switch[newPath[i]].dpid_port[newPath[i+1]]
                                                msg.actions.append(of.ofp_action_output(port = pt_next_hope ))
                                                core.openflow.sendToDPID(newPath[i], msg) #switch i-esimo
                                            else:
                                                log.error("S_i-1 and S_i-1' should always be the same")
