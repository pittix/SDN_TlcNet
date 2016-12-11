class Switches():
    switches = []

    def addSwitch(swID, porte):
        switches[swID]= porte
    def delSwitch(swID):
        switches[swID]= None

    def mac2Port(swID,macAddr):
        if(switch[swID] is None):
            return
        for sw in switch[swID]:
            if port.mac == macAddr :
                return port.num
            else:
                continue
    def listSwitches():
        listSw=self.switches
        return listSw

class Ports():
    port = []
    def addPort(portNum, macAddr, state, feature):
        details.num=portNum
        details.mac=macAddr
        details.status=state
        details.feats=feature
        port.append(details)
    def delPort(portNum):
        for pos in self.port:
            if pos.num == portNum:
                infos=(pos.mac,pos.status,pos.feats)
                del self.port[pos]
                return infos
