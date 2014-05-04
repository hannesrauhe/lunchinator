"""Base class for Lunch Server Controller classes"""
import sys
from lunchinator import get_server, get_settings, log_info, log_error, get_notification_center
from lunchinator.lunch_datathread_threading import DataReceiverThread, DataSenderThread
from lunchinator.utilities import processPluginCall
from lunchinator.notification_center import NotificationCenter

class LunchServerController(object):
    def __init__(self):
        super(LunchServerController, self).__init__()
        self._initNotificationCenter()
        
    def _initNotificationCenter(self):
        NotificationCenter.setSingletonInstance(NotificationCenter())
        
    def initDone(self):
        pass
    
    def call(self, msg, peerIDs, peerIPs):
        get_server()._perform_call(msg, peerIDs, peerIPs)

    def shutdown(self):
        if get_server().is_running():
            get_server().stop_server()
        else:
            # server is not running. HELO_STOP will not have any effect.
            self._coldShutdown()
            
    def _coldShutdown(self):
        """Shutdown when server is not yet running"""
        sys.exit(0)
    
    def extendMemberInfo(self, _infoDict):
        """Add some specific information to the info dictionary"""
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

    def serverStopped(self, _exit_code):
        get_settings().write_config_to_hd()
        if get_server().get_plugins_enabled():
            for pluginInfo in get_server().plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    pluginInfo.plugin_object.deactivate()
