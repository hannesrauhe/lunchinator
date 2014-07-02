from lunchinator import get_peers, get_peer_actions, log_warning
from functools import partial
from lunchinator.peer_actions.peer_actions_singleton import PeerActions

def _fillPeerActionsMenu(popupMenu, peerID, filterFunc):
    peerInfo = get_peers().getPeerInfo(pID=peerID)
    actionsDict = get_peer_actions().getPeerActions(peerID, peerInfo, filterFunc)
    if actionsDict:
        actionKeys = sorted(actionsDict.keys())
        for actionKey in actionKeys:
            actions = actionsDict[actionKey]
            if actionKey == PeerActions.STANDARD_PEER_ACTIONS_KEY:
                displayedName = "General"
            else:
                displayedName = actions[0].getPluginObject().get_displayed_name()
                if not displayedName:
                    displayedName = actionKey
            header = popupMenu.addAction(displayedName)
            header.setEnabled(False)
            
            for action in actions:
                popupMenu.addAction(action.getName(), partial(action.performAction, peerID, peerInfo))
    return popupMenu

def initializePeerActionsMenu(menu, peerID, filterFunc):
    menu.clear()
    if not get_peers():
        log_warning("no lunch_peers instance available, cannot show peer actions")
        return menu
    
    if peerID:
        _fillPeerActionsMenu(menu, peerID, filterFunc)
    return menu

def showPeerActionsPopup(peerID, filterFunc, parent):
    from PyQt4.QtGui import QMenu, QCursor
    if not get_peers():
        log_warning("no lunch_peers instance available, cannot show peer actions")
        return
    if peerID:
        popupMenu = _fillPeerActionsMenu(QMenu(parent), peerID, filterFunc)
        popupMenu.exec_(QCursor.pos())
        popupMenu.deleteLater()
            
