#!/usr/bin/python
# coding=utf-8

from time import strftime, localtime, time, mktime, gmtime
import socket, sys, os, json, codecs, contextlib
from threading import Lock
from cStringIO import StringIO

from lunchinator import log_debug, log_info, log_critical, get_settings, log_exception, log_error, log_warning, \
    convert_string
from lunchinator.utilities import determineOwnIP
     
import tarfile
import platform
from lunchinator.lunch_peers import LunchPeers
import random

EXIT_CODE_ERROR = 1
EXIT_CODE_UPDATE = 2
EXIT_CODE_STOP = 3
EXIT_CODE_NO_QT = 42
        
class lunch_server(object):
    _instance = None
    
    @classmethod
    def get_singleton_server(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        super(lunch_server, self).__init__()
        self.controller = None
        self.initialized = False
        self._load_plugins = True
        self.running = False
        self.update_request = False
        self.new_msg = False
        self.my_master = -1    
        self.peer_ip = None  # the IP of the peer i contacted to be my master
        self.last_lunch_call = 0
        self.last_messages = []
        self.plugin_manager = None
        self.no_updates = False
        self.own_ip = None
        self.messagesLock = Lock()
        self.unknown_cmd = ["HELO_REQUEST_INFO", "HELO_INFO"]
        
        self.exitCode = 0  
        
        
    """ -------------------------- CALLED FROM MAIN THREAD -------------------------------- """
        
    """Initialize Lunch Server with a specific controller"""
    def initialize(self, controller=None):
        if self.initialized:
            return
        self.initialized = True
        
        if controller != None:
            self.controller = controller
        else:
            from lunchinator.lunch_server_controller import LunchServerController
            self.controller = LunchServerController()
            
        self._peers = LunchPeers(self.controller)
        self._read_config()

        if self.get_plugins_enabled():  
            from iface_plugins import iface_called_plugin, iface_general_plugin, iface_gui_plugin, PluginManagerSingleton
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

    '''listening method - should be started in its own thread'''    
    def start_server(self):
        self.initialize()
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Starting the lunch notifier service")
        self.running = True
        self.my_master = -1  # the peer i use as master
        announce_name = -1  # how often did I announce my name
        
        self.own_ip = determineOwnIP()
        
        is_in_broadcast_mode = False
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            self.controller.initDone()
            while self.running:
                if self.new_msg and (time() - mktime(self.getMessage(0)[0])) > (get_settings().get_reset_icon_time() * 60):
                    self.new_msg = False
                try:
                    daten, addr = s.recvfrom(1024)
                    ip = unicode(addr[0])
                    try:
                        daten = daten.decode('utf-8')
                    except:
                        log_error("Received illegal data from %s, maybe wrong encoding" % ip)
                        continue
                    self._peers.seenPeer(ip)
                        
                    if self._check_group(daten, ip):
                        if daten.startswith("HELO"):
                            # simple infrastructure protocol messages starting with HELO''' 
                            self._incoming_event(daten, ip)                            
                        else:  
                            # simple message                          
                            self._incoming_call(daten, ip)
                    else:
                        log_debug("Dropped a message from", ip, daten)
                except socket.timeout:
                    # TODO only group members?
                    if len(self._peers)>1:                        
                        if is_in_broadcast_mode:
                            is_in_broadcast_mode = False
                            log_warning("ending braodcast")
                            
                        if not self.own_ip:
                            self.own_ip = self._determineOwnIP()
                        if announce_name == -1:
                            # first start
                            self.call("HELO_REQUEST_INFO " + self._build_info_string())
                        if announce_name == 10:
                            # it's time to announce my name again and switch the master
                            self.call("HELO " + get_settings().get_user_name())
                            announce_name = 0
                            self._remove_inactive_peers()
                            self._call_for_dict()
                        else:
                            # just wait for the next time when i have to announce my name
                            announce_name += 1
                    else:
                        if not is_in_broadcast_mode:
                            is_in_broadcast_mode = True
                            log_warning("seems like you are alone - broadcasting for others")
                        self._broadcast()
                    # log_debug("Current Members:", self._peers.getActivePeers())
        except socket.error as e:
            # socket error messages may contain special characters, which leads to crashes on old python versions
            log_error(u"stopping lunchinator because of socket error:", convert_string(str(e)))
        except:
            log_exception("stopping - Critical error: %s" % str(sys.exc_info())) 
        finally: 
            try:
                self.call("HELO_LEAVE bye")
                s.close()  
            except:
                log_warning("Wasn't able to send the leave call and close the socket...")
            self._finish()            
            
    
    """ -------------------------- CALLED FROM ARBITRARY THREAD -------------------------- """
    def changeGroup(self, newgroup):
        log_info("Changing Group: %s -> %s" % (get_settings().get_group(), newgroup))
        get_settings().set_group(newgroup)
        self.call("HELO_LEAVE Changing Group")
        self.call("HELO_REQUEST_INFO " + self._build_info_string())
    
    def messagesCount(self):
        length = 0
        self.messagesLock.acquire()
        try:
            length = len(self.last_messages)
        finally:
            self.messagesLock.release()
        return length
    
    def getMessage(self, index):
        message = None
        self.messagesLock.acquire()
        try:
            message = self.last_messages[index]
        finally:
            self.messagesLock.release()
        return message
    
    def lockMessages(self):
        # this is annoying
        #log_debug("Getting Messages with lock")
        self.messagesLock.acquire()
        
    def releaseMessages(self):
        #log_debug("lock released")
        self.messagesLock.release()
        
    def getMessages(self, begin=None):
        self.lockMessages()
        messages = []
        try:
            if not begin:  
                messages = self.last_messages[:]
            else:
                for mtime, addr, msg in self.last_messages:                    
                    if mtime >= gmtime(begin):
                        messages.append([mtime, addr, msg])
                    else:
                        break
        finally:
            self.releaseMessages()
        return messages
    
    def get_plugins_enabled(self):
        return self._load_plugins
    
    def set_plugins_enabled(self, enable):
        self._load_plugins = enable
    
    def getLunchPeers(self):
        """Deprecated. Use lunchinator.get_peers()"""
        return self._peers
        
    def getOwnIP(self):
        # TODO replace by getOwnID if possible
        return self.own_ip
    
    def getAvailableDBConnections(self):
        if not self.get_plugins_enabled():
            log_error("Plugins are disabled, cannot get DB connections.")
            return None
        
        from iface_plugins import PluginManagerSingleton
        pluginInfo = PluginManagerSingleton.get().getPluginByName("Database Settings", "general")
        if pluginInfo and pluginInfo.plugin_object.is_activated:
            return pluginInfo.plugin_object.getAvailableDBConnections()
        log_exception("getAvailableDBConnections: DB Connections plugin not yet loaded")
        return None        
        
    def getDBConnection(self, name=""):
        if not self.get_plugins_enabled():
            log_error("Plugins are disabled, cannot get DB connections.")
            return None
        
        from iface_plugins import PluginManagerSingleton
        pluginInfo = PluginManagerSingleton.get().getPluginByName("Database Settings", "general")
        if pluginInfo and pluginInfo.plugin_object.is_activated:
            return pluginInfo.plugin_object.getDBConnection(name)
        log_exception("getDBConnection: DB Connections plugin not yet loaded")
        return None        
        

    def call(self, msg, client='', hosts=[]):
        self.initialize()
        
        target = None
        if client:
            # send to client regardless of the dontSendTo state
            target = [client.strip()]
        elif 0 == len(hosts):
            # TODO determine whether to send to everyone or only to members
            target = self._peers.getSendTargets()
        else:
            # send to all specified hosts regardless of groups or dontSendTo
            target = set(hosts)
        
        if 0 == len(target):
            log_error("Cannot send message, no peers connected, no peer found in members file")

        i = 0
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        try:      
            for ip in target:
                try:
                    log_debug("Sending", msg, "to", ip.strip())
                    s.sendto(msg.encode('utf-8'), (ip.strip(), 50000))
                    i += 1
                except:
                    # only warning message; happens sometimes if the host is not reachable
                    log_warning("Message %s could not be delivered to %s: %s" % (s, ip, str(sys.exc_info()[0])))
                    continue
        finally:
            s.close() 
        return i
        
    '''short for the call function above for backward compatibility'''
    def call_all_members(self, msg):        
        self.call(msg)   
            
    """ ---------------------- PRIVATE -------------------------------- """
    
    def _finish(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Stopping the lunch notifier service")
        self._peers.finish()
        self._write_messages_to_file()
        self.controller.serverStopped(self.exitCode)
        
    def _read_config(self):              
        if len(self.last_messages) == 0:
            self.last_messages = self._init_messages_from_file()
    
    def _updatePeersDict(self, otherDict, noLocal=True):
        # TODO expect peer IDs in dict
        for ip, peerName in otherDict.items():
            if noLocal and ip.startswith('127'):
                continue
            
            self._peers.peerNameReceived(None, ip, peerName)
        
    def _init_messages_from_file(self):
        messages = []
        if os.path.exists(get_settings().get_messages_file()):
            try:
                with codecs.open(get_settings().get_messages_file(), 'r', 'utf-8') as f:    
                    tmp_msg = json.load(f)
                    for m in tmp_msg:
                        messages.append([localtime(m[0]), m[1], m[2]])
            except:
                log_exception("Could not read messages file %s,but it seems to exist" % (get_settings().get_messages_file()))
        return messages
    
    def _write_messages_to_file(self):
        try:
            if self.messagesCount() > 0:
                with codecs.open(get_settings().get_messages_file(), 'w', 'utf-8') as f:
                    f.truncate()
                    msg = []
                    self.messagesLock.acquire()
                    try:
                        for m in self.last_messages:
                            msg.append([mktime(m[0]), m[1], m[2]])
                    finally:
                        self.messagesLock.release()
                    json.dump(msg, f)
        except:
            log_exception("Could not write messages to %s: %s" % (get_settings().get_messages_file(), sys.exc_info()[0]))    
    
    def _build_info_string(self):
        from lunchinator.utilities import getPlatform, PLATFORM_LINUX, PLATFORM_MAC, PLATFORM_WINDOWS
        info_d = {u"avatar": get_settings().get_avatar_file(),
                   u"name": get_settings().get_user_name(),
                   u"group": get_settings().get_group(),
                   u"next_lunch_begin":get_settings().get_default_lunch_begin(),
                   u"next_lunch_end":get_settings().get_default_lunch_end(),
                   u"version":get_settings().get_version_short(),
                   u"version_commit_count":get_settings().get_commit_count(),
                   u"version_commit_count_plugins":get_settings().get_commit_count_plugins(),
                   u"platform": sys.platform}
        
        if getPlatform() == PLATFORM_LINUX:
            info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.mac_ver())
        elif getPlatform() == PLATFORM_WINDOWS:
            info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.mac_ver())
        elif getPlatform() == PLATFORM_MAC:
            info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.mac_ver())
            
        if get_settings().get_next_lunch_begin():
            info_d[u"next_lunch_begin"] = get_settings().get_next_lunch_begin()
        if get_settings().get_next_lunch_end():
            info_d[u"next_lunch_end"] = get_settings().get_next_lunch_end()
        self.controller.extendMemberInfo(info_d)
        return json.dumps(info_d)      
        
    def _createPeersDict(self):
        peersDict = {}
        # TODO only group members?
        for peerID in self._peers.getActivePeers():
            ip = self._peers.getIPOfPeer(peerID)
            if ip == None:
                # should not happen
                continue
            # TODO add peer ID to dict
            if self._peers.getPeerInfo(peerID) != None and u'name' in self._peers.getPeerInfo(peerID):
                peersDict[ip] = self._peers.getPeerInfo(peerID)[u'name']
            else:
                peersDict[ip] = ip
        return peersDict
    
    def _check_group(self, data, addr):
        '''checks message for group commands, return false if peer is not in group'''
        if addr.startswith("127."):
            return True
                
        try:
            if " " in data:
                (cmd, value) = data.split(" ", 1)
                if cmd.startswith("HELO_INFO"):
                    self._update_peer_info(addr, json.loads(value), requestAvatar=False)
                elif cmd.startswith("HELO_REQUEST_INFO"):
                    self._update_peer_info(addr, json.loads(value), requestAvatar=False)
                    self.call("HELO_INFO " + self._build_info_string(), client=addr)
        except:
            log_exception("was not able to parse Info from", data, addr)
        
        peerID = self._peers.getPeerID(addr)
        return peerID != None and self._peers.isMember(peerID)
        
        
    def _incoming_call(self, msg, addr):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8")
        peerID = self._peers.getPeerID(addr)
        m = self._peers.getPeerName(peerID)
            
        log_info("%s: [%s] %s" % (t, m, msg))
        
        self._insertMessage(mtime, addr, msg)
        self.controller.messagePrepended(mtime, addr, msg)
        self.new_msg = True
        self._write_messages_to_file()
        
        if not msg.startswith("ignore"):
            self.controller.processMessage(msg, addr)
            
            from lunchinator.utilities import getTimeDifference
            if get_settings().get_lunch_trigger() in msg.lower() and 0 < getTimeDifference(get_settings().get_alarm_begin_time(), get_settings().get_alarm_end_time()):
                timenum = mktime(mtime)
                if timenum - self.last_lunch_call > get_settings().get_mute_timeout():
                    self.last_lunch_call = timenum
                    self.controller.processLunchCall(msg, addr)
                else:
                    log_debug("messages will not trigger alarm: %s: [%s] %s until %s (unless you change the setting, that is)" % (t, m, msg, strftime("%H:%M:%S", localtime(timenum + get_settings().get_mute_timeout()))))
      
    def _update_peer_info(self, ip, newInfo, requestAvatar=True):   
        peerID = self._peers.updatePeerInfo(ip, newInfo)
            
        if requestAvatar:
            # Request avatar if not there yet
            if u"avatar" in self._peers.getPeerInfo(peerID):
                if not os.path.exists(get_settings().get_avatar_dir() + "/" + self._peers.getPeerInfo(peerID)[u"avatar"]):
                    self.call("HELO_REQUEST_AVATAR " + str(self.controller.getOpenTCPPort(ip)), client=ip)     
      
    def _incoming_event(self, data, ip):   
        if ip.startswith("127."):
            # stop command is only allowed from localhost :-)
            if data.startswith("HELO_STOP"):
                log_info("Got Stop Command from localhost: %s" % data)
                self.running = False
                self.exitCode = EXIT_CODE_STOP  # run_forever script will stop
            # only stop command is allowed from localhost, returning here
            return     
                
        try:        
            (cmd, value) = data.split(" ", 1)
                
            if cmd.startswith("HELO_REQUEST_DICT"):
                self._update_peer_info(ip, json.loads(value))
                self.call("HELO_DICT " + json.dumps(self._createPeersDict()), client=ip)                   
                
            elif cmd.startswith("HELO_DICT"):
                # the master send me the list of all members - yeah
                ext_members = json.loads(value)
                self._updatePeersDict(ext_members)
                if self.my_master == -1:
                    self.call("HELO_REQUEST_INFO " + self._build_info_string())
                    
                self.my_master = ip
                                    
            elif cmd.startswith("HELO_LEAVE"):
                # the sender tells me, that he is going
                self._peers.peerLeft(ip)
                self.call("HELO_DICT " + json.dumps(self._createPeersDict()), client=ip)
               
            elif cmd.startswith("HELO_AVATAR"):
                # someone wants to send me his pic via TCP
                values = value.split()
                file_size = int(values[0].strip())
                tcp_port = 0  # 0 means we must guess the port
                if len(values) > 1:
                    tcp_port = int(values[1].strip())
                file_name = ""
                peerID = self._peers.getPeerID(ip)
                if self._peers.getPeerInfo(peerID) != None and u"avatar" in self._peers.getPeerInfo(peerID):
                    file_name = os.path.join(get_settings().get_avatar_dir(), self._peers.getPeerInfo(peerID)["avatar"])
                else:
                    log_error("%s tried to send his avatar, but I don't know where to safe it" % (ip))
                
                if len(file_name):
                    self.controller.receiveFile(ip, file_size, file_name, tcp_port)
                
            elif cmd.startswith("HELO_REQUEST_AVATAR"):
                # someone wants my pic 
                other_tcp_port = get_settings().get_tcp_port()
                
                try:                    
                    other_tcp_port = int(value.strip())
                except:
                    log_exception("%s requested avatar, I could not parse the port from value %s, using standard %d" % (str(ip), str(value), other_tcp_port))
                    
                fileToSend = get_settings().get_avatar_dir() + "/" + get_settings().get_avatar_file()
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    log_info("Sending file of size %d to %s : %d" % (fileSize, str(ip), other_tcp_port))
                    self.call("HELO_AVATAR %s" % fileSize, ip)
                    # TODO in a future release, send TCP port
                    # self.call("HELO_AVATAR %s %s" % (fileSize, other_tcp_port), ip)
                    self.controller.sendFile(ip, fileToSend, other_tcp_port)
                else:
                    log_error("Want to send file %s, but cannot find it" % (fileToSend))   
                
            elif cmd.startswith("HELO_REQUEST_LOGFILE"):
                # someone wants my logfile 
                other_tcp_port = get_settings().get_tcp_port()
                try:                
                    (oport, _) = value.split(" ", 1)    
                    other_tcp_port = int(oport.strip())
                except:
                    log_exception("%s requested the logfile, I could not parse the port and number from value %s, using standard %d and logfile 0" % (str(ip), str(value), other_tcp_port))
                
                fileToSend = StringIO()
                with contextlib.closing(tarfile.open(mode='w:gz', fileobj=fileToSend)) as tarWriter:
                    if os.path.exists(get_settings().get_log_file()):
                        tarWriter.add(get_settings().get_log_file(), arcname="0.log")
                    logIndex = 1
                    while os.path.exists("%s.%d" % (get_settings().get_log_file(), logIndex)):
                        tarWriter.add("%s.%d" % (get_settings().get_log_file(), logIndex), arcname="%d.log" % logIndex)
                        logIndex = logIndex + 1
                
                fileSize = fileToSend.tell()
                log_info("Sending file of size %d to %s : %d" % (fileSize, str(ip), other_tcp_port))
                self.call("HELO_LOGFILE_TGZ %d %d" % (fileSize, other_tcp_port), ip)
                self.controller.sendFile(ip, fileToSend.getvalue(), other_tcp_port, True)
            elif "HELO" == cmd:
                # someone tells me his name
                didKnowMember = self._peers.knowsIP(ip)
                self._peers.peerNameReceived(None, ip, value)
                if not didKnowMember:
                    self.call("HELO_INFO " + self._build_info_string(), client=ip)
            elif cmd not in self.unknown_cmd:
                # Report unknown commands once
                self.unknown_cmd.append(cmd)
                log_info("received unknown command from %s: %s with value %s" % (ip, cmd, value))        
            
            self.controller.processEvent(cmd, value, ip)
        except:
            log_exception("Unexpected error while handling HELO call: %s" % (str(sys.exc_info())))
            log_critical("The data received was: %s" % data)
    
    def _insertMessage(self, mtime, addr, msg):
        self.messagesLock.acquire()
        try:
            self.last_messages.insert(0, [mtime, addr, msg])
        finally:
            self.messagesLock.release()
                    
    def _remove_inactive_peers(self):
        try:
            peersToRemove = self._peers.getTimedOutPeers(get_settings().get_peer_timeout())
            log_debug("Removing inactive peers:", peersToRemove)
            with self._peers:
                self._peers.removePeers(peersToRemove)
        except:
            log_exception("Something went wrong while trying to clean up the list of active members")
            
    def _call_for_dict(self):
        '''ask for the dictionary and send over own information'''
        try:
            if len(self._peers.getActivePeers()) > 0:
                # request from random peer
                randPeerID = random.sample(self._peers.getActivePeers(), 1)[0]
                self.call("HELO_REQUEST_DICT " + self._build_info_string(), client=self._peers.getIPOfPeer(randPeerID))
        except:
            log_exception("Something went wrong while trying to send a call to the new master")
    
    def _broadcast(self):
        try:
            s_broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s_broad.sendto('HELO_REQUEST_INFO ' + self._build_info_string(), ('255.255.255.255', 50000))
            s_broad.close()
        except:
            log_exception("Problem while broadcasting")
