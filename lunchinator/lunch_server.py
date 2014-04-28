#!/usr/bin/python
# coding=utf-8

from time import strftime, localtime, time, mktime, gmtime
import socket, sys, os, json, codecs, contextlib
from threading import Lock
from cStringIO import StringIO

from lunchinator import log_debug, log_info, log_critical, get_settings, log_exception, log_error, log_warning, \
    convert_string
from lunchinator.utilities import getTimeDifference
     
import tarfile
import platform
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
        self._has_gui = True
        self.running = False
        self.update_request = False
        self.new_msg = False
        self.my_master = -1    
        self.peer_nr = 0  # the number of the peer i contacted to be my master
        self.last_lunch_call = 0
        self.last_messages = []
        self._members = []
        self._peer_timeout = {}
        self._peer_info = {}
        self.plugin_manager = None
        self.no_updates = False
        self.own_ip = ""
        self.messagesLock = Lock()
        self.membersLock = Lock()
        self.dontSendTo = set()
        self.unknown_cmd = ["HELO_REQUEST_INFO", "HELO_INFO"]
        self._peer_groups = set()
        
        self.exitCode = 0  
        
        
    """ -------------------------- CALLED FROM MAIN THREAD -------------------------------- """
        
    """Initialize Lunch Server with a specific controller"""
    def initialize(self, controller=None):
        if self.initialized:
            return
        self.initialized = True
        
        self._read_config()
        
        if controller != None:
            self.controller = controller
        else:
            from lunchinator.lunch_server_controller import LunchServerController
            self.controller = LunchServerController()

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
        
        self._determineOwnIP()
        
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
                    if ip not in self._peer_timeout:
                        self._peer_timeout[ip] = time() 
                        self._peerAppended(ip)
                    else:
                        self._peer_timeout[ip] = time()
                        
                    if self._check_group(daten, ip):
                        if not ip.startswith("127."):
                            if not ip in self._members:
                                self._append_member(ip, ip)
                            
                        if daten.startswith("HELO"):
                            # simple infrastructure protocol messages starting with HELO''' 
                            self._incoming_event(daten, ip)                            
                        else:  
                            # simple message                          
                            self._incoming_call(daten, ip)
                    else:
                        log_debug("Dropped a message from", ip, daten)
                except socket.timeout:
                    if len(self._members) > 1:                        
                        if is_in_broadcast_mode:
                            is_in_broadcast_mode = False
                            log_warning("ending braodcast")
                            
                        if not len(self.own_ip):
                            self._determineOwnIP()
                        if announce_name == -1:
                            # first start
                            self.call("HELO_REQUEST_INFO " + self._build_info_string())
                        if announce_name == 10:
                            # it's time to announce my name again and switch the master
                            self.call("HELO " + get_settings().get_user_name())
                            announce_name = 0
                            self._remove_inactive_members()
                            self._call_for_dict()
                        else:
                            # just wait for the next time when i have to announce my name
                            announce_name += 1
                    else:
                        if not is_in_broadcast_mode:
                            is_in_broadcast_mode = True
                            log_warning("seems like you are alone - broadcasting for others")
                        self._broadcast()
                    # log_debug("Current Members:", self._members)
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
            
    def perform_call(self, msg, client, hosts):
        """Called from main thread"""     
        msg = convert_string(msg)
        client = convert_string(client)
        
        target = None
        if client:
            # send to client regardless of the dontSendTo state
            target = [client.strip()]
        elif 0 == len(hosts):
            # we're not on the lunchinator thread, so lock
            self.lockMembers()
            try:
                target = set(self._members) - self.dontSendTo
            finally:
                self.releaseMembers()
        else:
            # send to all specified hosts regardless of the dontSendTo state
            target = set(convert_string(h) for h in hosts)
        
        if 0 == len(target):
            log_error("Cannot send message, no peers connected, no peer found in _members file")
            
        if self.has_gui() and \
           get_settings().get_warn_if_members_not_ready() and \
           not msg.startswith(u"HELO") and \
           get_settings().get_lunch_trigger().upper() in msg.upper():
            # check if everyone is ready
            notReadyMembers = set()
            self.lockMembers()
            try:
                for m in self.get_members():
                    if not self.is_peer_ready(m):
                        notReadyMembers.add(self.memberName(m))
            finally:
                self.releaseMembers()
            
            if notReadyMembers:
                    
                if len(notReadyMembers) == 1:
                    warn = "%s is not ready for lunch." % iter(notReadyMembers).next()
                elif len(notReadyMembers) == 2:
                    it = iter(notReadyMembers)
                    warn = "%s and %s are not ready for lunch." % (it.next(), it.next())
                else:
                    warn = "%s and %d others are not ready for lunch." % (random.sample(notReadyMembers, 1)[0], len(notReadyMembers) - 1)
                try:
                    from PyQt4.QtGui import QMessageBox
                    warn = "WARNING: %s Send lunch call anyways?" % warn
                    result = QMessageBox.warning(None,
                                                 "Members not ready",
                                                 warn,
                                                 buttons=QMessageBox.Yes | QMessageBox.No,
                                                 defaultButton=QMessageBox.No)
                    if result == QMessageBox.No:
                        return
                except:
                    print "WARNING: %s" % warn

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
            
    
    """ -------------------------- CALLED FROM ARBITRARY THREAD -------------------------- """
    def changeGroup(self, newgroup):
        log_info("Changing Group: %s -> %s" % (get_settings().get_group(), newgroup))
        get_settings().set_group(newgroup)
        self.call("HELO_LEAVE Changing Group")
        self.call("HELO_REQUEST_INFO " + self._build_info_string())
                    
    def memberName(self, addr):
        if addr in self._peer_info and u'name' in self._peer_info[addr]:
            return self._peer_info[addr][u'name']
        return addr
    
    def ipForMemberName(self, name):
        for ip, infoDict in self._peer_info.iteritems():
            if u'name' in infoDict and infoDict[u'name'] == name:
                return ip
        return None
    
    def messagesCount(self):
        length = 0
        self.lockMessages()
        try:
            length = len(self.last_messages)
        finally:
            self.releaseMessages()
        return length
    
    def getMessage(self, index):
        message = None
        self.lockMessages()
        try:
            message = self.last_messages[index]
        finally:
            self.releaseMessages()
        return message
    
    def lockMessages(self):
        self.messagesLock.acquire()
        
    def releaseMessages(self):
        self.messagesLock.release()
        
    def lockMembers(self):
        self.membersLock.acquire()
        
    def releaseMembers(self):
        self.membersLock.release()
                    
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
            
    def get_groups(self):  
        return self._peer_groups
    
    def get_members(self):  
        return self._members

    def get_member_timeout(self):  
        return self._peer_timeout    
    
    def get_peer_timeout(self):  
        return self._peer_timeout    
    
    def get_plugins_enabled(self):
        return self._load_plugins
    
    def set_plugins_enabled(self, enable):
        self._load_plugins = enable
        
    def has_gui(self):
        return self._has_gui
    
    def set_has_gui(self, enable):
        self._has_gui = enable
    
    def get_peer_info(self):  
        return self._peer_info   
    
    def is_peer_readyness_known(self, peer_addr):
        return peer_addr in self._peer_info and \
               u"next_lunch_begin" in self._peer_info[peer_addr] and \
               u"next_lunch_end"  in self._peer_info[peer_addr]
    
    def is_peer_ready(self, peer_addr):
        if self._peer_info.has_key(peer_addr):
            p = self._peer_info[peer_addr]
            if p.has_key(u"next_lunch_begin") and p.has_key(u"next_lunch_end"):
                diff = getTimeDifference(p[u"next_lunch_begin"], p[u"next_lunch_end"])
                if diff == None:
                    # illegal format, just assume ready
                    return True
                return getTimeDifference(p[u"next_lunch_begin"], p[u"next_lunch_end"]) > 0
        # no information, just assume ready
        return True
        
    def getOwnIP(self):
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
    
    def getController(self):
        return self.controller
        
    def call_info(self, peers=[]):
        '''An info call informs a peer about my name etc...
        by default to every peer'''
        if 0 == len(peers):
            peers = self._peer_info.keys()
        return self.call("HELO_INFO " + self._build_info_string(), hosts=peers) 
        
    def call_request_info(self, peers=[]):
        '''An info call informs a peer about my name etc... and ask for his/hers
        by default to every peer'''
        if 0 == len(peers):
            peers = self._peer_info.keys()
        return self.call("HELO_REQUEST_INFO " + self._build_info_string(), hosts=peers)  
    
    def call(self, msg, client='', hosts=[]):
        self.initialize()
        self.controller.call(msg, client, hosts)
        
    '''short for the call function above for backward compatibility'''
    def call_all_members(self, msg):        
        self.call(msg)   
            
    """ ---------------------- PRIVATE -------------------------------- """
    
    def _finish(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Stopping the lunch notifier service")
        self._write_members_to_file()
        self._write_messages_to_file()
        self.controller.serverStopped(self.exitCode)
        
    def _read_config(self):              
        if len(self._members) == 0:
            self._init_members_from_file()
        if len(self.last_messages) == 0:
            self.last_messages = self._init_messages_from_file()
    
    def _updateMembersDict(self, otherDict, noLocal=True):
        for ip, hostn in otherDict.items():
            if noLocal and ip.startswith('127'):
                continue
            
            if not ip in self._members:
                self._append_member(ip, hostn)
        
    def _memberAppended(self, ip):
        self.controller.memberAppended(ip, self._peer_info[ip])
    
    def _memberUpdated(self, ip):
        self.controller.memberUpdated(ip, self._peer_info[ip])
    
    def _memberRemoved(self, ip):
        self.controller.memberRemoved(ip)
    
    def _peerAppended(self, ip):
        self.controller.peerAppended(ip)
        
    def _append_member(self, ip, hostn, inform=True):
        # insert name into info dict
        memberInfo = {}
        if ip in self._peer_info:
            memberInfo = self._peer_info[ip]
        memberInfo[u'name'] = hostn
        
        self.lockMembers()
        didAppend = False
        didUpdate = False
        try:
            self._peer_info[ip] = memberInfo
            if not ip in self._members:
                self._members.append(ip)
                if inform:
                    didAppend = True
            elif inform:
                didUpdate = True
        finally:
            self.releaseMembers()
            
        if didAppend:
            self._memberAppended(ip)
        if didUpdate:
            self._memberUpdated(ip)
            
    
    def _remove_member(self, ip):
        didRemove = False        
        self.lockMembers()
        try:
            if ip in self._members:
                self._members.remove(ip)
                didRemove = True
        finally:
            self.releaseMembers()
            
        if didRemove:
            self._memberRemoved(ip)
            
    def _init_members_from_file(self):
        members = []
        if os.path.exists(get_settings().get_members_file()):
            with codecs.open(get_settings().get_members_file(), 'r', 'utf-8') as f:    
                for hostn in f.readlines():
                    hostn = hostn.strip()
                    if len(hostn) == 0:
                        continue
                    try:
                        ip = unicode(socket.gethostbyname(hostn))
                        self._append_member(ip, hostn, False)
                    except:
                        log_warning("cannot find host specified in members_file by %s with name %s" % (get_settings().get_members_file(), hostn))
        return members
    
    def _write_members_to_file(self):
        try:
            if len(self._members) > 1:
                with codecs.open(get_settings().get_members_file(), 'w', 'utf-8') as f:
                    f.truncate()
                    for m in self._members:
                        f.write(m + "\n")
        except:
            log_exception("Could not write _members to %s" % (get_settings().get_members_file()))
            
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
                    self.lockMessages()
                    try:
                        for m in self.last_messages:
                            msg.append([mktime(m[0]), m[1], m[2]])
                    finally:
                        self.releaseMessages()
                    json.dump(msg, f)
        except:
            log_exception("Could not write messages to %s: %s" % (get_settings().get_messages_file(), sys.exc_info()[0]))    
    
    def _build_info_string(self):
        from lunchinator.utilities import getPlatform, PLATFORM_LINUX, PLATFORM_MAC, PLATFORM_WINDOWS
        info_d = {u"avatar": get_settings().get_avatar_file(),
                   u"name": get_settings().get_user_name(),
                   u"group": get_settings().get_group(),
                   u"next_lunch_begin":get_settings().get_next_lunch_begin(),
                   u"next_lunch_end":get_settings().get_next_lunch_end(),
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
            
        self.controller.extendMemberInfo(info_d)
        return json.dumps(info_d)      
        
    def _createMembersDict(self):
        membersDict = {}
        for ip in self._members:
            if ip in self._peer_info and u'name' in self._peer_info[ip]:
                membersDict[ip] = self._peer_info[ip][u'name']
            else:
                membersDict[ip] = ip
        return membersDict
    
    '''checks message for group commands, return false if peer is not in group'''
    def _check_group(self, data, addr):
        if addr.startswith("127."):
            return True        
        own_group = get_settings().get_group()
        
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
        
        if len(own_group) == 0:
            # accept anything as long as i do not have a group
            return True
            
        return self._peer_info.has_key(addr) and self._peer_info[addr].has_key("group") and self._peer_info[addr]["group"] == own_group
        
    def _incoming_call(self, msg, addr):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8")
        m = self.memberName(addr)
            
        log_info("%s: [%s] %s" % (t, m, msg))
        
        self._insertMessage(mtime, addr, msg)
        self.controller.messagePrepended(mtime, addr, msg)
        self.new_msg = True
        self._write_messages_to_file()
        
        if not msg.startswith("ignore"):
            self.controller.processMessage(msg, addr)
            
            diff = getTimeDifference(get_settings().get_alarm_begin_time(), get_settings().get_alarm_end_time())
            if diff == None or get_settings().get_lunch_trigger() in msg.lower() and 0 < diff:
                timenum = mktime(mtime)
                if timenum - self.last_lunch_call > get_settings().get_mute_timeout():
                    self.last_lunch_call = timenum
                    self.controller.processLunchCall(msg, addr)
                else:
                    log_debug("messages will not trigger alarm: %s: [%s] %s until %s (unless you change the setting, that is)" % (t, m, msg, strftime("%H:%M:%S", localtime(timenum + get_settings().get_mute_timeout()))))
      
    def _update_peer_info(self, ip, newInfo, requestAvatar=True):            
        peer_group = newInfo["group"] if newInfo.has_key("group") else ""     
        peer_name = newInfo["name"] if newInfo.has_key("name") else ip
        own_group = get_settings().get_group()       
        
        group_unchanged = self._peer_info.has_key(ip) and self._peer_info[ip].has_key("group") and self._peer_info[ip] == peer_group
        self.lockMembers()
        try:
            self._peer_info[ip] = newInfo
        finally:
            self.releaseMembers()
        
        if group_unchanged:
            if peer_group == own_group:
                self._memberUpdated(ip)
        else:
            if peer_group not in self._peer_groups:
                self._peer_groups.add(peer_group)
                self.controller.groupAppended(peer_group, self._peer_groups)
            if peer_group == own_group:
                self._append_member(ip, peer_name)
                self._memberUpdated(ip)
            else:
                self._remove_member(ip)
            
        if requestAvatar:
            # Request avatar if not there yet
            if self._peer_info[ip].has_key("avatar"):
                if not os.path.exists(get_settings().get_avatar_dir() + "/" + self._peer_info[ip]["avatar"]):
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
                self.call("HELO_DICT " + json.dumps(self._createMembersDict()), client=ip)                   
                
            elif cmd.startswith("HELO_DICT"):
                # the master send me the list of _members - yeah
                ext_members = json.loads(value)
                self._updateMembersDict(ext_members)
                if self.my_master == -1:
                    self.call("HELO_REQUEST_INFO " + self._build_info_string())
                    
                self.my_master = ip
                                    
            elif cmd.startswith("HELO_LEAVE"):
                # the sender tells me, that he is going
                if ip in self._members:
                    self.lockMembers()
                    try:
                        self._members.remove(ip)
                    finally:
                        self.releaseMembers()
                    self._memberRemoved(ip)
                self.call("HELO_DICT " + json.dumps(self._createMembersDict()), client=ip)
               
            elif cmd.startswith("HELO_AVATAR"):
                # someone wants to send me his pic via TCP
                values = value.split()
                file_size = int(values[0].strip())
                tcp_port = 0  # 0 means we must guess the port
                if len(values) > 1:
                    tcp_port = int(values[1].strip())
                file_name = ""
                if self._peer_info[ip].has_key("avatar"):
                    file_name = os.path.join(get_settings().get_avatar_dir(), self._peer_info[ip]["avatar"])
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
                didKnowMember = ip in self._members
                self._append_member(ip, value) 
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
        self.lockMessages()
        try:
            self.last_messages.insert(0, [mtime, addr, msg])
        finally:
            self.releaseMessages()
                    
    def _remove_inactive_members(self):
        try:
            indicesToRemove = []
            for memberIndex, ip in enumerate(self._members):
                if ip in self._peer_timeout:
                    if time() - self._peer_timeout[ip] > get_settings().get_peer_timeout():
                        indicesToRemove.append(memberIndex)
                else:
                    indicesToRemove.append(memberIndex)
                    
            log_debug("Removing inactive _members: %s (%s)" % ([self._members[i] for i in indicesToRemove], indicesToRemove))
            for memberIndex in reversed(indicesToRemove):
                self._memberRemoved(self._members[memberIndex])
            self.lockMembers()
            try:
                for memberIndex in reversed(indicesToRemove):
                    del self._members[memberIndex]
            finally:
                self.releaseMembers()
        except:
            log_exception("Something went wrong while trying to clean up the _members-list")
            
    '''ask for the dictionary and send over own information'''
    def _call_for_dict(self):
        try:
            if len(self._members) > self.peer_nr:
                self.call("HELO_REQUEST_DICT " + self._build_info_string(), client=self._members[self.peer_nr])
            if len(self._members) > 0:
                self.peer_nr = (self.peer_nr + 1) % len(self._members)
        except:
            log_exception("Something went wrong while trying to send a call to the new master")
    
    def _determineOwnIP(self):  
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)      
        for m in self._members:
            try:
                # connect to UDF discard port 9
                s.connect((m, 9))
                self.own_ip = unicode(s.getsockname()[0])
                break
            except:
                log_debug("While getting own IP, problem to connect to", m)
                continue
        log_debug("Found my IP:", self.own_ip)
        s.close()
    
    def _broadcast(self):
        try:
            s_broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s_broad.sendto('HELO_REQUEST_INFO ' + self._build_info_string(), ('255.255.255.255', 50000))
            s_broad.close()
        except:
            log_exception("Problem while broadcasting")
