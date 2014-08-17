"""Base class for Lunch Server Controller classes"""
import sys
from lunchinator import get_server, get_settings, log_info, get_notification_center,\
    log_debug, get_peers, log_exception, get_plugin_manager, convert_string,\
    get_peer_actions, logs_debug, log_error
    
from lunchinator.lunch_datathread_threading import DataReceiverThread, DataSenderThread
from lunchinator.utilities import processPluginCall, getTimeDifference,\
    formatException
from lunchinator.notification_center import NotificationCenter
from time import localtime, strftime
from lunchinator.peer_actions import PeerActions

class LunchServerController(object):
    def __init__(self):
        super(LunchServerController, self).__init__()
        self.last_lunch_call = 0
        self._initNotificationCenter()
        get_notification_center().connectPluginActivated(self._checkSendInfoDict)
        get_notification_center().connectPluginDeactivated(self._checkSendInfoDict)
        
    def _initNotificationCenter(self):
        NotificationCenter.setSingletonInstance(NotificationCenter())
        
    def initDone(self):
        pass
    
    def initPlugins(self):
        if get_settings().get_plugins_enabled():
            from yapsy.PluginManager import PluginManagerSingleton
            from lunchinator.plugin import NotificationPluginManager
            
            PluginManagerSingleton.setBehaviour([
                NotificationPluginManager,
            ])
            self.plugin_manager = PluginManagerSingleton.get()
            self.plugin_manager.app = self
            self.plugin_manager.setConfigParser(get_settings().get_config_file(), get_settings().write_config_to_hd)
            self.plugin_manager.setPluginPlaces(get_settings().get_plugin_dirs())

            try:
                self.plugin_manager.collectPlugins()
            except:
                log_exception("problem when loading plugins")
            
            get_peer_actions().initialize()
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
    
    def extendMemberInfo(self, infoDict):
        """Add some specific information to the info dictionary"""
        if not get_settings().get_plugins_enabled():
            return
        for pluginInfo in get_plugin_manager().getAllPlugins():
            if pluginInfo.plugin_object.is_activated and pluginInfo.plugin_object.extendsInfoDict():
                try:
                    pluginInfo.plugin_object.extendInfoDict(infoDict)
                except:
                    log_exception(u"plugin error in %s while extending member info" % pluginInfo.name)
    
    def getOpenTCPPort(self, senderIP):
        return DataReceiverThread.getOpenPort(category="avatar%s" % senderIP)
    
    def receiveFile(self, ip, fileSize, fileName, tcp_port, successFunc=None, errorFunc=None):
        if tcp_port == 0:
            tcp_port = self.getOpenTCPPort()
        log_info("Receiving file of size %d on port %d"%(fileSize,tcp_port))
        dr = DataReceiverThread.receiveSingleFile(ip, fileName, fileSize, tcp_port, successFunc, errorFunc)
        dr.start()
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData=False):
        if isData:
            ds = DataSenderThread.sendData(ip, otherTCPPort, fileOrData)
        else:
            ds = DataSenderThread.sendSingleFile(ip, otherTCPPort, fileOrData)
        ds.start()
    
    def processEvent(self, cmd, value, addr, _eventTime, newPeer, fromQueue):
        """ process any non-message event """
        action = None
        msgData = None
        if cmd.startswith(u"HELO"):
            prefix = cmd[5:]
            action = PeerActions.get().getPeerAction(prefix)
            
            peerID = get_peers().getPeerID(pIP=addr)
            if action is not None:
                if peerID is None:
                    log_error(u"Could not get peer ID for IP", addr)
                    return
                
                try:
                    msgData = action.preProcessMessageData(value)
                except:
                    log_error("Error preprocessing data for peer action %s: %s" % (action.getName(), formatException()))
                    return
                
                if action.willIgnorePeerAction(msgData):
                    if logs_debug():
                        log_debug("Ignore",
                                  "peer action", action.getPluginName(), ":", action.getName(),
                                  "from peer:", peerID, 
                                  "message:", value)
                    return
                
                if action.hasCategories():
                    category = action.getCategoryFromMessage(msgData)
                else:
                    category = None
                
                shouldProcess = PeerActions.get().shouldProcessMessage(action, category, peerID, self.getMainGUI(), msgData)
                
                if logs_debug():
                    log_debug("Accept" if shouldProcess else "Reject",
                              "peer action", action.getPluginName(), ":", action.getName(),
                              "from peer:", peerID,
                              "" if category is None else "category " + category)
                
                if not shouldProcess:
                    return
        
        processPluginCall(addr, lambda p, ip, member_info: p.process_event(cmd, value, ip, member_info, msgData), newPeer, fromQueue, action)
    
    def getMainGUI(self):
        return None
    
    def _checkSendInfoDict(self, pluginName, category):
        pluginName = convert_string(pluginName)
        category = convert_string(category)
        pi = get_plugin_manager().getPluginByName(pluginName, category)
        if pi != None:
            po = pi.plugin_object
            if po.extendsInfoDict():
                get_server().call_info()
    
    def _insertMessage(self,mtime, addr, msg):
        if get_server().get_messages() != None:
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
            get_plugin_manager().deactivatePlugins(get_plugin_manager().getAllPlugins(), save_state=False)
        get_notification_center().disconnectPluginActivated(self._checkSendInfoDict)
        get_notification_center().disconnectPluginDeactivated(self._checkSendInfoDict)
        get_notification_center().finish()
