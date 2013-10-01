"""Base class for Lunch Server Controller classes"""
from lunchinator import get_server
class LunchServerController(object):
    def __init__(self):
        super(LunchServerController, self).__init__()
        
    def initDone(self):
        pass
        
    def memberAppended(self, ip, infoDict):
        pass
    
    def memberUpdated(self, ip, infoDict):
        pass
    
    def memberRemoved(self, ip):
        pass
    
    def messagePrepended(self, messageTime, senderIP, messageText):
        pass
    
    def receiveFile(self, ip, fileSize, fileName):
        pass
    
    def sendFile(self, ip, filePath, otherTCPPort):
        pass
    
    def processEvent(self, cmd, hostName, senderIP):
        pass
    
    def serverStopped(self):
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                pluginInfo.plugin_object.deactivate()
