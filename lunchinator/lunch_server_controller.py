"""Base class for Lunch Server Controller classes"""
from lunchinator import get_server, get_settings, log_info, log_error
from lunchinator.lunch_datathread_threading import DataReceiverThread, DataSenderThread
from lunchinator.utilities import processPluginCall

class LunchServerController(object):
    def __init__(self):
        super(LunchServerController, self).__init__()
        
    def initDone(self):
        pass
        
    def memberAppended(self, ip, infoDict):
        log_error("IMPLEMENT memberAppended - remove this message")
        pass
        
    def groupAppended(self, group, peer_groups):
        pass
        
    def peerAppended(self, ip, infoDict):
        pass
    
    def peerUpdated(self, ip, infoDict):
        pass
    
    def peerRemoved(self, ip):
        pass    
    
    def messagePrepended(self, messageTime, senderIP, messageText):
        pass
    
    def extendMemberInfo(self, _infoDict):
        pass
    
    def getOpenTCPPort(self, _senderIP):
        # TODO really get open port
        return get_settings().get_tcp_port()
    
    def receiveFile(self, ip, fileSize, fileName, tcp_port):
        if tcp_port == 0:
            tcp_port = get_settings().get_tcp_port()
        log_info("Receiving file of size %d on port %d"%(fileSize,tcp_port))
        dr = DataReceiverThread(ip,fileSize,fileName,get_settings().get_tcp_port())
        dr.start()
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData = False):
        ds = DataSenderThread(ip,fileOrData, otherTCPPort, isData)
        ds.start()
    
    def processEvent(self, cmd, value, addr):
        """ process any non-message event """
        processPluginCall(addr, lambda p, ip, member_info: p.process_event(cmd, value, ip, member_info))
    
    def processMessage(self, msg, addr):
        """ process any message event, including lunch calls """
        processPluginCall(addr, lambda p, ip, member_info: p.process_message(msg, ip, member_info))
                    
    def processLunchCall(self, msg, addr):
        """ process a lunch call """
        processPluginCall(addr, lambda p, ip, member_info: p.process_lunch_call(msg, ip, member_info))
    
    def notifyUpdates(self):
        pass

    def serverStopped(self, _exit_code):
        get_settings().write_config_to_hd()
        if get_server().get_plugins_enabled():
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    pluginInfo.plugin_object.deactivate()
