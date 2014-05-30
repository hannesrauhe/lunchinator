from lunchinator.iface_plugins import iface_gui_plugin
from lunchinator import log_exception, get_settings, get_server,\
    get_notification_center, log_debug, get_peers, log_error, convert_string
import urllib2, sys, os, json
from datetime import datetime, timedelta
from lunchinator.utilities import getPlatform, PLATFORM_MAC, getValidQtParent
    
class private_messages(iface_gui_plugin):
    def __init__(self):
        super(private_messages, self).__init__()
        self._openChats = {} # mapping peer ID -> ChatDockWidget
        
    def activate(self):
        iface_gui_plugin.activate(self)
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        # TODO use this to browse messages history later
        from PyQt4.QtGui import QWidget
        # TODO remove this
        self._openChat("Corny", "Other", get_settings().get_resource("images", "me.png"), get_settings().get_resource("images", "lunchinator.png"), "otherID")
        return QWidget(parent)
    
    def destroy_widget(self):
        iface_gui_plugin.destroy_widget(self)
        
    def process_event(self, cmd, value, _ip, peerInfo):
        peerID = peerInfo[u"ID"]
        if cmd.startswith(u"HELO_PM_ACK"):
            mID = value.split()[0]
            self._processAck(peerID, mID)
        elif cmd.startswith(u"HELO_PM"):
            try:
                msgDict = json.loads(value)
                self._processMessage(peerID, msgDict)
            except:
                log_exception("Error processing private message from", peerID, "data:", value)
    
    def _processAck(self, otherID, mID):
        pass
    
    def _processMessage(self, otherID, msgDict):
        pass
    
    def _sendMessage(self, otherID, msgHTML):
        print msgHTML
    
    def _activateChat(self, chatWindow):
        chatWindow.show()
        if getPlatform() == PLATFORM_MAC:
            chatWindow.activateWindow()
        chatWindow.raise_()
    
    def _openChat(self, myName, otherName, myAvatar, otherAvatar, otherID):
        from private_messages.chat_window import ChatWindow
        newWindow = ChatWindow(getValidQtParent(), myName, otherName, myAvatar, otherAvatar, otherID)
        newWindow.windowClosing.connect(self._chatClosed)
        newWindow.getChatWidget().sendMessage.connect(self._sendMessage)
        self._openChats[otherID] = newWindow
        self._activateChat(newWindow)
        
    def _chatClosed(self, pID):
        pID = convert_string(pID)
        if pID in self._openChats:
            chatWindow = self._openChats[pID]
            chatWindow.deleteLater()
            del self._openChats[pID]
        else:
            log_error("Closed chat window was not maintained:", pID)
        
    def openChat(self, pID):
        if pID in self._openChats:
            self._activateChat(self._openChats[pID])
        
        otherName = get_peers().getPeerName(pID=pID)
        if otherName == None:
            log_error("Could not get info of chat partner", pID)
            return
        otherAvatar = get_peers().getPeerAvatarFile(pID=pID)
        if not otherAvatar:
            otherAvatar = get_settings().get_resource("images", "lunchinator.png")
        
        myName = get_settings().get_user_name()
        myAvatar = get_settings().get_avatar_file()
        if not os.path.exists(myAvatar):
            myAvatar = get_settings().get_resource("images", "me.png")
        
        self._openChat(myName, otherName, myAvatar, otherAvatar, pID)

if __name__ == '__main__':
    pm = private_messages()
    pm.run_in_window()
