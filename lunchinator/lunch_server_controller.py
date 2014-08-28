"""Base class for Lunch Server Controller classes"""
import sys
from lunchinator import get_server, get_settings, get_notification_center,\
    get_peers, get_plugin_manager, convert_string,\
    get_peer_actions
from lunchinator.log import getCoreLogger, loggingFunc
from lunchinator.datathread.dt_threading import DataReceiverThread, DataSenderThread
from lunchinator.utilities import getTimeDifference, formatException
from lunchinator.notification_center import NotificationCenter
from time import localtime, strftime
from lunchinator.peer_actions import PeerActions
from lunchinator.lunch_peers import LunchPeers

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
                getCoreLogger().exception("problem when loading plugins")
            
            get_peer_actions().initialize()
        else:
            getCoreLogger().info("lunchinator initialised without plugins")
    
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
                    getCoreLogger().exception(u"plugin error in %s while extending member info" % pluginInfo.name)
    
    def getOpenTCPPort(self, senderIP):
        return DataReceiverThread.getOpenPort(category="avatar%s" % senderIP)
    
    def receiveFile(self, ip, fileSize, fileName, tcp_port, successFunc=None, errorFunc=None):
        if tcp_port == 0:
            tcp_port = self.getOpenTCPPort()
        getCoreLogger().info("Receiving file of size %d on port %d", fileSize, tcp_port)
        dr = DataReceiverThread.receiveSingleFile(ip, fileName, fileSize, tcp_port, getCoreLogger(), None, successFunc, errorFunc)
        dr.start()
    
    def sendFile(self, ip, fileOrData, otherTCPPort, isData=False):
        if isData:
            ds = DataSenderThread.sendData(ip, otherTCPPort, fileOrData, getCoreLogger())
        else:
            ds = DataSenderThread.sendSingleFile(ip, otherTCPPort, fileOrData, getCoreLogger())
        ds.start()
    
    def processEvent(self, xmsg, addr, _eventTime, newPeer, fromQueue):
        """ process any non-message event 
        @type xmsg: extMessageIncoming
        @type addr: unicode
        @type _eventTime: float
        @type newPeer: bool
        @type fromQueue: bool
        """
        msgData = None
        
        cmd = xmsg.getCommand()
        value = xmsg.getCommandPayload()
        
        action = PeerActions.get().getPeerAction(cmd)
        
        peerID = get_peers().getPeerID(pIP=addr)
        if action is not None:
            if peerID is None:
                getCoreLogger().error(u"Could not get peer ID for IP %s", addr)
                return
            
            try:
                msgData = action.preProcessMessageData(value)
            except:
                getCoreLogger().error("Error preprocessing data for peer action %s: %s", action.getName(), formatException())
                return
            
            if action.willIgnorePeerAction(msgData):
                getCoreLogger().debug("Ignore peer action %s.%s from peer %s (message: %s)",
                          action.getPluginName(), action.getName(),
                          peerID, value)
            
            if action.hasCategories():
                category = action.getCategoryFromMessage(msgData)
            else:
                category = None
            
            shouldProcess = PeerActions.get().shouldProcessMessage(action, category, peerID, self.getMainGUI(), msgData)
            
            getCoreLogger().debug(u"%s peer action %s.%s from peer %s%s"
                              "Accept" if shouldProcess else "Reject",
                              action.getPluginName(), action.getName(),
                              peerID, ("" if category is None else " category " + category))
            
            if not shouldProcess:
                return
        
        self.processPluginCall(addr, lambda p, ip, member_info: p.process_command(xmsg, ip, member_info, msgData), newPeer, fromQueue, action)
        #deprecated:
        self.processPluginCall(addr, lambda p, ip, member_info: p.process_event("HELO_"+cmd, value, ip, member_info, msgData), newPeer, fromQueue, action)
    
    def _processCallOnPlugin(self, pluginObject, pluginName, ip, call, newPeer, fromQueue, member_info):
        from lunchinator.plugin import iface_called_plugin, iface_gui_plugin
        
        # called also contains gui plugins
        if not (isinstance(pluginObject, iface_called_plugin) or \
                isinstance(pluginObject, iface_gui_plugin)):
            getCoreLogger().warning("Plugin '%s' is not a called/gui plugin", pluginName)
            return
        if pluginObject.is_activated:
            try:
                if (pluginObject.processes_events_immediately() and not fromQueue) or \
                   (not pluginObject.processes_events_immediately() and not newPeer):
                    call(pluginObject, ip, member_info)
            except:
                pluginObject.logger.exception(u"plugin error in %s while processing event" % pluginName)
        
    def processPluginCall(self, ip, call, newPeer, fromQueue, action=None):
        """ call plugins
        @type ip: unicode
        @type call: function
        @type newPeer: bool
        @type fromQueue: bool
        @type action: PeerAction   
        """
        if not get_settings().get_plugins_enabled():
            return
        
        member_info = get_peers().getPeerInfo(pIP=ip)
        
        # called also contains gui plugins
        for pluginInfo in get_plugin_manager().getPluginsOfCategory("called")+get_plugin_manager().getPluginsOfCategory("gui"):
            # if this is a peer action, only call special plugins
            if action is None or (pluginInfo.plugin_object.processes_all_peer_actions() and \
                                  pluginInfo.name != action.getPluginName()):
                self._processCallOnPlugin(pluginInfo.plugin_object, pluginInfo.name, ip, call, newPeer, fromQueue, member_info)
        
        # perform peer action
        if action is not None:
            self._processCallOnPlugin(action.getPluginObject(), action.getPluginName(), ip, call, newPeer, fromQueue, member_info)
            
    def getMainGUI(self):
        return None
    
    @loggingFunc
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
        
    def processMessage(self, xmsg, addr, eventTime, newPeer, fromQueue):
        """ process any message event, including lunch calls
        @type xmsg: extMessageIncoming
        @type addr: unicode
        @type eventTime: float
        @type newPeer: bool
        @type fromQueue: bool
        """
        mtime = localtime(eventTime)
        t = strftime("%a, %d %b %Y %H:%M:%S", mtime).decode("utf-8")        
        msg = xmsg.getPlainMessage()
        
        if not newPeer:
            with get_peers():
                m = get_peers().getPeerInfo(pIP=addr, lock=False)
                peerName = get_peers().getDisplayedPeerName(pIP=addr, lock=False)
            if m is None:
                getCoreLogger().error("Error processing message: info dict is None")
            else:
                if peerName is None:
                    peerName = m.get(LunchPeers.PEER_NAME_KEY, "<unknown>")
                getCoreLogger().info("%s: [%s (%s)] %s", t, peerName, m[LunchPeers.PEER_ID_KEY], msg)
                self._insertMessage(mtime, m[LunchPeers.PEER_ID_KEY], msg)
                get_notification_center().emitMessagePrepended(mtime, m[LunchPeers.PEER_ID_KEY], msg)
        else:
            m = {u"ID": addr}
        
        
        processLunchCall = False
        #deprecated:
        self.processPluginCall(addr, lambda p, ip, member_info: p.process_message(msg, ip, member_info), newPeer, fromQueue)
        
        if get_settings().get_lunch_trigger() in msg.lower():
            # check if we should process the lunch call
            diff = getTimeDifference(get_settings().get_alarm_begin_time(), get_settings().get_alarm_end_time(), getCoreLogger())
            if diff == None or 0 < diff:
                # either the time format is invalid or we are within the alarm time
                if eventTime - self.last_lunch_call > get_settings().get_mute_timeout() or \
                   fromQueue and self.last_lunch_call == eventTime:
                    # either the lunch call is within a mute timeout or
                    # this is a queued lunch call that previously wasn't muted
                    processLunchCall = True
            
            if processLunchCall:
                self.last_lunch_call = eventTime
                #deprecated:
                self.processPluginCall(addr, lambda p, ip, member_info: p.process_lunch_call(msg, ip, member_info), newPeer, fromQueue)
            else:
                getCoreLogger().debug("messages will not trigger alarm: %s: [%s] %s until %s (unless you change the setting, that is)", t, m, msg, strftime("%H:%M:%S", localtime(eventTime + get_settings().get_mute_timeout())))
        
        self.processPluginCall(addr, lambda p, ip, member_info: p.process_group_message(xmsg, ip, member_info, processLunchCall), newPeer, fromQueue)
            
    def serverStopped(self, _exit_code):
        get_settings().write_config_to_hd()
        if get_settings().get_plugins_enabled():
            get_plugin_manager().deactivatePlugins(get_plugin_manager().getAllPlugins(), save_state=False)
        get_notification_center().disconnectPluginActivated(self._checkSendInfoDict)
        get_notification_center().disconnectPluginDeactivated(self._checkSendInfoDict)
        get_notification_center().finish()
