"""Base class for Lunch Server Controller classes"""
import sys
from lunchinator import get_server, get_settings, log_info, get_notification_center,\
    log_debug, get_peers, log_exception, get_plugin_manager
from lunchinator.lunch_datathread_threading import DataReceiverThread, DataSenderThread
from lunchinator.utilities import processPluginCall, getTimeDifference
from lunchinator.notification_center import NotificationCenter
from time import localtime, strftime, mktime

class LunchServerController(object):
    def __init__(self):
        super(LunchServerController, self).__init__()
        self.last_lunch_call = 0
        self._initNotificationCenter()
        
    def _initNotificationCenter(self):
        NotificationCenter.setSingletonInstance(NotificationCenter())
        
    def initDone(self):
        pass
    
    def initPlugins(self):
        if get_settings().get_plugins_enabled():  
            from yapsy.PluginManager import PluginManagerSingleton
            from iface_plugins import iface_called_plugin, iface_general_plugin, iface_gui_plugin
            from iface_db_plugin import iface_db_plugin
            from yapsy.ConfigurablePluginManager import ConfigurablePluginManager
            
            PluginManagerSingleton.setBehaviour([
                ConfigurablePluginManager,
            ])
            self.plugin_manager = PluginManagerSingleton.get()
            self.plugin_manager.app = self
            self.plugin_manager.setConfigParser(get_settings().get_config_file(), get_settings().write_config_to_hd)
            self.plugin_manager.setPluginPlaces(get_settings().get_plugin_dirs())
            categoriesFilter = {
               "general" : iface_general_plugin,
               "called" : iface_called_plugin,
               "gui" : iface_gui_plugin,
               "db" : iface_db_plugin
               }
            self.plugin_manager.setCategoriesFilter(categoriesFilter) 

            try:
                self.plugin_manager.collectPlugins()
            except:
                log_exception("problem when loading plugins")
            
            for p in self.plugin_manager.getAllPlugins():
                if p.plugin_object.is_activation_forced() and not p.plugin_object.is_activated:
                    self.plugin_manager.activatePluginByName(p.name, p.category)
                    
        else:
            log_info("lunchinator initialised without plugins")
    
    def call(self, msg, peerIDs, peerIPs):
        get_server().perform_call(msg, peerIDs, peerIPs)

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
    
    def processEvent(self, cmd, value, addr, _eventTime, newPeer, fromQueue):
        """ process any non-message event """
        processPluginCall(addr, lambda p, ip, member_info: p.process_event(cmd, value, ip, member_info), newPeer, fromQueue)
    
    def _insertMessage(self,mtime, addr, msg):
        if get_server().get_messages():
            get_server().get_messages().insert(mtime, addr, msg)
        
    def processMessage(self, msg, addr, eventTime, newPeer, fromQueue):
        """ process any message event, including lunch calls """
        mtime = localtime(eventTime)
        t = strftime("%a, %d %b %Y %H:%M:%S", mtime).decode("utf-8")
        
        if not newPeer:
            m = get_peers().getPeerInfo(pIP=addr)
            log_info("%s: [%s] %s" % (t, m[u"ID"], msg))
            self._insertMessage(mtime, m[u"ID"], msg)
            get_notification_center().emitMessagePrepended(mtime, m[u"ID"], msg)
        else:
            m = {u"ID": addr}
        
        if not msg.startswith("ignore"):
            processPluginCall(addr, lambda p, ip, member_info: p.process_message(msg, ip, member_info), newPeer, fromQueue)
            
            if get_settings().get_lunch_trigger() in msg.lower():
                processLunchCall = False
                # check if we should process the lunch call
                diff = getTimeDifference(get_settings().get_alarm_begin_time(), get_settings().get_alarm_end_time())
                if diff == None or 0 < diff:
                    # either the time format is invalid or we are within the alarm time
                    if eventTime - self.last_lunch_call > get_settings().get_mute_timeout() or \
                       fromQueue and self.last_lunch_call == eventTime:
                        # either the lunch call is within a mute timeout or
                        # this is a queued lunch call that previously wasn't muted
                        processLunchCall = True
                
                if processLunchCall:
                    self.last_lunch_call = eventTime
                    processPluginCall(addr, lambda p, ip, member_info: p.process_lunch_call(msg, ip, member_info), newPeer, fromQueue)
                else:
                    log_debug("messages will not trigger alarm: %s: [%s] %s until %s (unless you change the setting, that is)" % (t, m, msg, strftime("%H:%M:%S", localtime(eventTime + get_settings().get_mute_timeout()))))
        
    def serverStopped(self, _exit_code):
        get_settings().write_config_to_hd()
        if get_settings().get_plugins_enabled():
            for pluginInfo in get_plugin_manager().getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    pluginInfo.plugin_object.deactivate()
        get_notification_center().finish()
