from lunchinator.peer_actions.peer_action import PeerAction
from lunchinator import get_peers, convert_string
from lunchinator.log import getCoreLogger

class ChangeDisplayedNameAction(PeerAction):
    def getName(self):
        return u"Change Displayed Name"
    
    def performAction(self, peerID, _peerInfo, _parent):
        try:
            from PyQt4.QtGui import QInputDialog
            oldName = get_peers().getDisplayedPeerName(pID=peerID)
            customName, ok = QInputDialog.getText(None, u"Custom Peer Name", u"Enter the displayed peer name:", text=oldName)
            if ok:
                customName = convert_string(customName)
                get_peers().setCustomPeerName(peerID, customName)
        except:
            getCoreLogger().exception("Error changing displayed peer name.")
            
    def peerMustBeOnline(self):
        return False
    
class ResetCustomPeerNameAction(PeerAction):
    def getName(self):
        return u"Reset Displayed Name"
    
    def performAction(self, peerID, _peerInfo, _parent):
        get_peers().setCustomPeerName(peerID, None)

    def appliesToPeer(self, peerID, _peerInfo):
        return get_peers().hasCustomPeerName(pID=peerID)
            
    def peerMustBeOnline(self):
        return False

def getStandardPeerActions():
    return [ChangeDisplayedNameAction(), ResetCustomPeerNameAction()]