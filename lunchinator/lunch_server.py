#!/usr/bin/python
# coding=utf-8


import socket, sys, os, json, codecs, contextlib, tarfile, platform, random
from time import strftime, localtime, time, mktime, gmtime
from threading import Lock
from cStringIO import StringIO

from lunchinator import log_debug, log_info, log_critical, get_settings, log_exception, log_error, log_warning, \
    convert_string
from lunchinator.utilities import determineOwnIP
from lunchinator.lunch_peers import LunchPeers

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
        self.new_msg = False
        self._peer_nr = 0
        self.last_lunch_call = 0
        self.last_messages = []
        self.plugin_manager = None
        self.own_ip = None
        self.messagesLock = Lock()
        
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
       
            
    """ -------------------------- CALLED FROM ARBITRARY THREAD -------------------------- """
    def call(self, msg, peerIDs=[], peerIPs=[]):
        '''Sends a call to the given peers, specified by either there IDs or there IPs'''
        self.initialize()        
        self.controller.call(msg, set(peerIDs), set(peerIPs))
                
    def call_info(self, peerIPs=[]):
        '''An info call informs a peer about my name etc...    by default to every peer'''
        if 0 == len(peerIPs):
            peerIPs = self._peers.getPeerIPs()
        return self.call("HELO_INFO " + self._build_info_string(), peerIPs=peerIPs)  
  
    def call_request_info(self, peerIPs=[]):
        '''Similar to a info call but also request information from the peer
        by default to every/from every peer'''
        if 0 == len(peerIPs):
            peers = self._peers.getPeerIPs()
        return self.call("HELO_REQUEST_INFO " + self._build_info_string(), peerIPs=peerIPs)
    
    def call_dict(self, ip):  
        '''Sends the information about my peers to one peer at a time'''      
        peers_dict = {}
        for ip in self._peers.getPeerIPs():
            peers_dict[ip] = self._peers.getPeerName(ip)
        self.call("HELO_DICT " + json.dumps(peers_dict), peerIPs=[ip]) 
        
    def call_request_dict(self):
        '''round robin I ask every peer for his peers, but one by one.
        (Sometimes the member asked is referred to as master)'''
        peers = self._peers.getPeerIPs()
        if len(peers) > self._peer_nr:
            self.call("HELO_REQUEST_DICT " + self._build_info_string(), peerIPs=[peers[self._peer_nr]])
        if len(peers):
            self._peer_nr = (self._peer_nr + 1) % len(peers)            
    
    def changeGroup(self, newgroup):
        log_info("Changing Group: %s -> %s" % (get_settings().get_group(), newgroup))
        get_settings().set_group(newgroup)
        self.call("HELO_LEAVE Changing Group")
        self._peers.removeMembers()
        self.call_request_info()
               
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
        
    def has_gui(self):
        return self._has_gui
    
    def set_has_gui(self, enable):
        self._has_gui = enable 
        
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
        
    def getLunchPeers(self):
        return self._peers 
    
    def getController(self):
        return self.controller

    '''listening method - should be started in its own thread'''    
    def start_server(self):
        self.initialize()
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Starting the lunch notifier service")
        self.running = True
        self.my_master = -1  # the peer i use as master
        announce_name = -1  # how often did I announce my name
        cmd = ""
        value = ""
        
        self.own_ip = determineOwnIP(self._peers.getPeerIPs())
        
        is_in_broadcast_mode = False
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            self.controller.initDone()
            while self.running:
                # TODO we can replace this with a signal when a message arrives, can't we?
                if self.new_msg and (time() - mktime(self.getMessage(0)[0])) > (get_settings().get_reset_icon_time() * 60):
                    self.new_msg = False
                try:
                    data, addr = s.recvfrom(1024)
                    ip = unicode(addr[0])
                    try:
                        data = data.decode('utf-8')
                    except:
                        log_error("Received illegal data from %s, maybe wrong encoding" % ip)
                        continue                 
                     
                    # check for local address: only stop command allowed, else ignore
                    if ip.startswith("127."):
                        if data.startswith("HELO_STOP"):
                            log_info("Got Stop Command from localhost: %s" % data)
                            self.running = False
                            self.exitCode = EXIT_CODE_STOP
                        continue
                    
                    # first we save the timestamp of this contact, no matter what
                    self._peers.seenIP(ip)
                    
                    # we also make sure, that there is a valid record for this ip,
                    # so we do not have to check this every time
                    self._peers.createPeerByIP(ip)
                    
                    # if there is no HELO in the beginning, it's just a message and 
                    # we handle it, if the peer is in our group
                    if not data.startswith("HELO"):
                        if self._peers.isMemberByIP(ip):
                            try:
                                self._handle_incoming_message(ip, data)
                            except:
                                log_exception("Error while handling incoming message from %s: %s" % (ip, data))
                        else:
                            log_debug("Dropped a message from %s: %s" % (ip, data))
                        continue
                    
                    try:
                        # commands must always have additional info:
                        (cmd, value) = data.split(" ", 1)
                    except:
                        log_error("Command of %s has no payload: %s" % (ip, data))
                    
                    # if this packet has info about the peer, we record it and
                    # are done
                    if self._handle_structure_event(ip, cmd, value):
                        continue
                                        
                    try:        
                        self._handle_incoming_event(ip, cmd, value)                         
                    except:
                        log_exception("Unexpected error while handling event from group member %s call: %s" % (ip, str(sys.exc_info())))
                        log_critical("The data received was: %s" % data)
                except socket.timeout:    
                    announce_name = (announce_name + 1) % 10
                        
                    if len(self._peers) > 1:                     
                        if is_in_broadcast_mode:
                            is_in_broadcast_mode = False
                            log_warning("ending braodcast")                            
                        if not self.own_ip:
                            self.own_ip = determineOwnIP(self._peers.getPeerIPs())
                        if announce_name == 0:
                            unknownPeers = self._peers.getNewPeerIPs()
                            self.call_request_info(unknownPeers)
                            # it's time to announce my name again and switch the master
                            self.call("HELO " + get_settings().get_user_name(), peerIPs=self._peers.getPeerIPs())
                            self.call_request_dict()
                    
                            # clean up peers
                            self._peers.removeInactive()
                    else:
                        if not is_in_broadcast_mode:
                            is_in_broadcast_mode = True
                            log_warning("seems like you are alone - broadcasting for others")
                        self._broadcast()
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
            
    def stop_server(self, stop_any=False):
        '''this stops a running server thread
        Usually this will not do anything if there is no running thread within the process
        if stop_any is true it will send a stop call in case another instance has to be stopped'''
        
        if stop_any or self.running:
            self.call("HELO_STOP shutdown", peerIPs=set([u"127.0.0.1"]))
            # Just in case the call does not reach the socket:
            self.running = False
        else:
            log_warning("There is no running server to stop")

    """ ---------------------- PRIVATE -------------------------------- """
    def _perform_call(self, msg, peerIDs, peerIPs):
        """Only the controller should invoke this method -> Called from main thread
        both peerIDs and peerIPs should be sets"""     
        msg = convert_string(msg)
        target = []
        
        if len(peerIDs) == 0 and len(peerIPs) == 0:
            target = self._peers.getPeerIPs()
        else:
            target = peerIPs
            for pID in peerIDs:
                pIPs = self._peers.getPeerIPs(pID)
                if len(pIPs):
                    target += pIPs
                else:
                    log_warning("While calling: I do not know a peer with ID %s, ignoring " % pID)
            
        if 0 == len(target):            
            log_error("Cannot send message, there is no peer given or none found")
            
        if self.has_gui() and \
           get_settings().get_warn_if_members_not_ready() and \
           not msg.startswith(u"HELO") and \
           get_settings().get_lunch_trigger().upper() in msg.upper():
            # check if everyone is ready
            notReadyMembers = [ip for ip in target if self._peers.isPeerReadyByIP(ip)]
            
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
    
    def _build_info_string(self):
        from lunchinator.utilities import getPlatform, PLATFORM_LINUX, PLATFORM_MAC, PLATFORM_WINDOWS
        info_d = {u"avatar": get_settings().get_avatar_file(),
                   u"name": get_settings().get_user_name(),
                   u"group": get_settings().get_group(),
                   u"ID": get_settings().get_ID(),
                   u"next_lunch_begin":get_settings().get_default_lunch_begin(),
                   u"next_lunch_end":get_settings().get_default_lunch_end(),
                   u"version":get_settings().get_version(),
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
    
    def _handle_structure_event(self, ip, cmd, value):
        r_value = True
        
        if cmd == "HELO_INFO":
            self._peers.updatePeerInfoByIP(ip, json.loads(value))

        elif cmd == "HELO_REQUEST_INFO":
            self._peers.updatePeerInfoByIP(ip, json.loads(value))
            self.call_info()
                
        elif cmd == "HELO_REQUEST_DICT":
            self._peers.updatePeerInfoByIP(ip, json.loads(value))   
            self.call_dict(ip)           

        elif cmd == "HELO_DICT":
            # the master send me the list of _members - yeah
            ext_members = json.loads(value)
            # i add every entry and assume, the member is in my group
            # i will still ask the member itself 
            for m_ip, m_name in ext_members.iteritems():
                self._peers.createPeerByIP(m_ip, {u"name":m_name, u"group":get_settings().get_group()})

        elif cmd == "HELO_LEAVE":
            self._peers.removeMembersByIP(ip)
            
        elif cmd == "HELO":
            # this is just a ping with the members name
            self._peers.updatePeerInfoByIP(ip, {u"name":value})     
            
        else:
            r_value = False 
            
        # now it's the plugins' turn:
        self.controller.processEvent(cmd, value, ip)
            
        return r_value

    def requets_avatar(self, ip): 
        info = self._peers.getPeerInfoByIP(ip)
        if info and u"avatar" in info and not os.path.exists(os.path.join(get_settings().get_avatar_dir(), info[u"avatar"])):
            self.call("HELO_REQUEST_AVATAR " + str(self.controller.getOpenTCPPort(ip)), client=ip)  
            return True
        return False   
      
            
    def _handle_incoming_event(self, ip, cmd, value): 
        # todo: maybe from here on this should be in plugins?
        
        if cmd == "HELO_AVATAR":
            # someone wants to send me his pic via TCP
            values = value.split()
            file_size = int(values[0].strip())
            tcp_port = 0  # 0 means we must guess the port
            if len(values) > 1:
                tcp_port = int(values[1].strip())
            file_name = ""
            info = self._peers.getPeerInfoByIP(ip)
            if u"avatar" in info:
                file_name = os.path.join(get_settings().get_avatar_dir(), info[u"avatar"])
            else:
                log_error("%s tried to send his avatar, but I don't know where to safe it" % (ip))
            
            if len(file_name):
                self.controller.receiveFile(ip, file_size, file_name, tcp_port)
            
        elif cmd == "HELO_REQUEST_AVATAR":
            # someone wants my pic 
            other_tcp_port = get_settings().get_tcp_port()
            
            try:                    
                other_tcp_port = int(value.strip())
            except:
                log_exception("%s requested avatar, I could not parse the port from value %s, using standard %d" % (str(ip), str(value), other_tcp_port))
                
            fileToSend = os.path.join(get_settings().get_avatar_dir(), get_settings().get_avatar_file())
            if os.path.exists(fileToSend):
                fileSize = os.path.getsize(fileToSend)
                log_info("Sending file of size %d to %s : %d" % (fileSize, str(ip), other_tcp_port))
                self.call("HELO_AVATAR %s" % fileSize, ip)
                # TODO in a future release, send TCP port
                # self.call("HELO_AVATAR %s %s" % (fileSize, other_tcp_port), ip)
                self.controller.sendFile(ip, fileToSend, other_tcp_port)
            else:
                log_error("Want to send file %s, but cannot find it" % (fileToSend))   
            
        elif cmd == "HELO_REQUEST_LOGFILE":
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
        
        # now it's the plugins' turn:
        self.controller.processEvent(cmd, value, ip)
            
    def _handle_incoming_message(self, ip, msg):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8")
        m = self._peers.getPeerName(ip)
            
        log_info("%s: [%s] %s" % (t, m, msg))
        
        self._insertMessage(mtime, ip, msg)
        self.controller.messagePrepended(mtime, ip, msg)
        
        # TODO: Signal at this point, if this is necessary?
        self.new_msg = True
        self._write_messages_to_file()
        
        if not msg.startswith("ignore"):
            self.controller.processMessage(msg, ip)
            
            from lunchinator.utilities import getTimeDifference
            diff = getTimeDifference(get_settings().get_alarm_begin_time(), get_settings().get_alarm_end_time())
            if diff == None or get_settings().get_lunch_trigger() in msg.lower() and 0 < diff:
                timenum = mktime(mtime)
                if timenum - self.last_lunch_call > get_settings().get_mute_timeout():
                    self.last_lunch_call = timenum
                    self.controller.processLunchCall(msg, ip)
                else:
                    log_debug("messages will not trigger alarm: %s: [%s] %s until %s (unless you change the setting, that is)" % (t, m, msg, strftime("%H:%M:%S", localtime(timenum + get_settings().get_mute_timeout()))))
    
    
    def _finish(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Stopping the lunch notifier service")
        self._peers.finish()
        self._write_messages_to_file()
        self.controller.serverStopped(self.exitCode)
    
    def _broadcast(self):
        try:
            s_broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s_broad.sendto('HELO_REQUEST_INFO ' + self._build_info_string(), ('255.255.255.255', 50000))
            s_broad.close()
        except:
            log_exception("Problem while broadcasting")
                        
    ''' ===== natural language messages writing and loading to/from file===== '''           
    def _read_config(self):              
        if len(self.last_messages) == 0:
            self.last_messages = self._init_messages_from_file()
        
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
            

    def _insertMessage(self, mtime, addr, msg):
        self.lockMessages()
        try:
            self.last_messages.insert(0, [mtime, addr, msg])
        finally:
            self.releaseMessages()
    
