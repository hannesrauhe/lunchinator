from lunchinator import get_peers, get_peer_actions, log_warning
from functools import partial
from lunchinator.peer_actions.peer_actions_singleton import PeerActions

def _fillPeerActionsMenu(popupMenu, peerID, filterFunc, parentWidget):
    peerInfo = get_peers().getPeerInfo(pID=peerID)
    actionsDict = get_peer_actions().getPeerActions(peerID, peerInfo, filterFunc)
    if actionsDict:
        actionsList = [] # tuples (sort key, displayed name, [actions])
        
        first = True
        for actionKey in actionsDict:
            actions = actionsDict[actionKey]
            if actionKey == PeerActions.STANDARD_PEER_ACTIONS_KEY:
                displayedName = "General"
                sortKey = u""
            else:
                displayedName = actions[0].getPluginObject().get_displayed_name()
                if not displayedName:
                    displayedName = actionKey
                sortKey = displayedName
                    
            actionsList.append((sortKey, displayedName, actions))
        
        actionsList = sorted(actionsList, key=lambda tup:tup[0].lower())
        for _, displayedName, actions in actionsList:
            if not first:
                popupMenu.addSeparator()
            else:
                first = False
            header = popupMenu.addAction(displayedName)
            header.setEnabled(False)
            
            for action in actions:
                icon = action.getIcon()
                if icon is not None:
                    popupMenu.addAction(icon, action.getDisplayedName(peerID), partial(action.performAction, peerID, peerInfo, parentWidget))
                else:
                    popupMenu.addAction(action.getDisplayedName(peerID), partial(action.performAction, peerID, peerInfo, parentWidget))
    return popupMenu

def initializePeerActionsMenu(menu, peerID, filterFunc, parentWidget):
    menu.clear()
    if get_peers() == None:
        log_warning("no lunch_peers instance available, cannot show peer actions")
        return menu
    
    if peerID:
        _fillPeerActionsMenu(menu, peerID, filterFunc, parentWidget)
    return menu

def showPeerActionsPopup(peerID, filterFunc, parent):
    from PyQt4.QtGui import QMenu, QCursor
    if get_peers() == None:
        log_warning("no lunch_peers instance available, cannot show peer actions")
        return
    if peerID:
        popupMenu = _fillPeerActionsMenu(QMenu(parent), peerID, filterFunc, parent)
        popupMenu.exec_(QCursor.pos())
        popupMenu.deleteLater()
            
