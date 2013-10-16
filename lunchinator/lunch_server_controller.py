"""Base class for Lunch Server Controller classes"""
from lunchinator import get_server, get_settings
from lunchinator.lunch_datathread_threading import DataReceiverThread, DataSenderThread
from lunchinator.iface_plugins import iface_called_plugin
from lunchinator.utilities import processPluginCall

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
        dr = DataReceiverThread(ip,fileSize,fileName,get_settings().get_tcp_port())
        dr.start()
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData = False):
        ds = DataSenderThread(ip,fileOrData, otherTCPPort, isData)
        ds.start()
    
    """ process any non-message event """
    def processEvent(self, cmd, value, addr):
        processPluginCall(addr, lambda p, ip, member_info: p.process_event(cmd, value, ip, member_info))
    
    """ process any message event, including lunch calls """
    def processMessage(self, msg, addr):
        processPluginCall(addr, lambda p, ip, member_info: p.process_message(msg, ip, member_info))
                    
    """ process a lunch call """
    def processLunchCall(self, msg, addr):
        processPluginCall(addr, lambda p, ip, member_info: p.process_lunch_call(msg, ip, member_info))

    def serverStopped(self, _exit_code):
        for pluginInfo in get_server().plugin_manager.getAllPlugins():
            if pluginInfo.plugin_object.is_activated:
                pluginInfo.plugin_object.deactivate()
        get_settings().write_config_to_hd()
