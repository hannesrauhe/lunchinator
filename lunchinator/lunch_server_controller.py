"""Base class for Lunch Server Controller classes"""
from lunchinator import get_server, get_settings, log_exception
from lunchinator.lunch_datathread_threading import DataReceiverThread, DataSenderThread

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
        dr = DataReceiverThread(self,ip,fileSize,fileName,get_settings().tcp_port)
        dr.start()
    
    def sendFile(self, ip, filePath, otherTCPPort):
        ds = DataSenderThread(self,ip,filePath, otherTCPPort)
        ds.start()
    
    def processEvent(self, cmd, value, addr):
        member_info = {}
        if get_server().member_info.has_key(addr):
            member_info = get_server().member_info[addr]
        for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("called")+get_server().plugin_manager.getPluginsOfCategory("gui"):
            if pluginInfo.plugin_object.is_activated:
                try:
                    pluginInfo.plugin_object.process_event(cmd,value,addr,member_info)
                except:
                    log_exception(u"plugin error in %s while processing event message" % pluginInfo.name)
    
    def serverStopped(self):
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                pluginInfo.plugin_object.deactivate()
