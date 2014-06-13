#!/usr/bin/python
# coding=utf-8

import socket, sys, os, json, contextlib, tarfile, platform, random, errno
from time import strftime, localtime, time
from cStringIO import StringIO

from lunchinator import log_debug, log_info, log_critical, get_settings, log_exception, log_error, log_warning, \
    convert_string
from lunchinator.lunch_peers import LunchPeers
from lunchinator.logging_mutex import loggingMutex
from collections import deque
from threading import Timer

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
        self._has_gui = True
        self._disable_broadcast = False
        self.running = False
        self._peer_nr = 0
        self._peers = None
        self.plugin_manager = None
        self._message_queues = {} # queues for messages from new peers
        self._last_messages = {} # last messages by peer ID, to avoid duplicates
        
        self.message_queues_lock = loggingMutex("message_queues", logging=get_settings().get_verbose())
        self.cached_messages_lock = loggingMutex("cached_messages", logging=get_settings().get_verbose())
        
        self.exitCode = 0  
        
    """ -------------------------- CALLED FROM MAIN THREAD -------------------------------- """
        
    def initialize(self, controller=None):
        """Initialize Lunch Server with a specific controller"""
        if self.initialized:
            return
        self.initialized = True
        
        if controller != None:
            self.controller = controller
        else:
            from lunchinator.lunch_server_controller import LunchServerController
            self.controller = LunchServerController()
            
        self._peers = LunchPeers()
        
        #TODO: Plugin init cannot be done in controller constructor because the GUI has to be ready
        #separation of gui Plugins necessary - but how *sigh*? 
        if get_settings().get_plugins_enabled():
            self.controller.initPlugins()
            from lunchinator.messages import Messages
            from lunchinator.peer_names import PeerNames
            self._messages = Messages(logging=get_settings().get_verbose())
            self._peerNames = PeerNames(logging=get_settings().get_verbose())
        else:
            self._messages = None 
            self._peerNames = None           
            
    """ -------------------------- CALLED FROM ARBITRARY THREAD -------------------------- """
    def call(self, msg, peerIDs=[], peerIPs=[]):
        '''Sends a call to the given peers, specified by either there IDs or there IPs'''
        assert(type(peerIPs) in [list,set])
        self.controller.call(msg, set(peerIDs), set(peerIPs))
        
    def call_all_members(self, msg):
        '''Sends a call to all members'''
        self.call(msg, self._peers.getMembers(), set())
                
    def call_info(self, peerIPs=[]):
        '''An info call informs a peer about my name etc...    by default to every peer'''
        if 0 == len(peerIPs):
            peerIPs = self._peers.getPeerIPs()
        return self.call("HELO_INFO " + self._build_info_string(), peerIPs=peerIPs)  
  
    def call_request_info(self, peerIPs=[]):
        '''Similar to a info call but also request information from the peer
        by default to every/from every peer'''
        if 0 == len(peerIPs):
            peerIPs = self._peers.getPeerIPs()
        return self.call("HELO_REQUEST_INFO " + self._build_info_string(), peerIPs=peerIPs)
    
    def call_dict(self, ip):  
        '''Sends the information about my peers to one peer identified by its IP at a time'''      
        peers_dict = {}
        for pIP in self._peers.getPeerIPs():
            peers_dict[pIP] = self._peers.getPeerName(pIP=pIP)
        self.call("HELO_DICT " + json.dumps(peers_dict), peerIPs=[ip]) 
        
    def call_request_dict(self):
        '''round robin I ask every peer for his peers, but one by one.
        (Sometimes the member asked is referred to as master)'''
        peers = self._peers.getPeerIPs()
        if len(peers) > self._peer_nr:
            self.call("HELO_REQUEST_DICT " + self._build_info_string(), peerIPs=[peers[self._peer_nr]])
        if len(peers):
            self._peer_nr = (self._peer_nr + 1) % len(peers)            
    
    def changeGroup(self, _newgroup):
        """Call get_setting().set_group(...) to change the group programatically."""
        self.call("HELO_LEAVE Changing Group")
        self._peers.removeMembersByIP()
        self.call_request_info()
               
    def get_messages(self):
        return self._messages
    
    def get_peer_names(self):
        return self._peerNames
        
    def is_running(self):
        return self.running
        
    def has_gui(self):
        return self._has_gui
    
    def set_has_gui(self, enable):
        self._has_gui = enable
        
    def set_disable_broadcast(self, disable):
        self._disable_broadcast = disable
        
    def get_disable_broadcast(self):
        return self._disable_broadcast
        
    def getLunchPeers(self):
        return self._peers 
    
    def getController(self):
        return self.controller

    '''listening method - should be started in its own thread'''    
    def start_server(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Starting the lunch notifier service")
        
        self.my_master = -1  # the peer i use as master
        
        is_in_broadcast_mode = False
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            self.running = True
            self._cleanupLock = loggingMutex("cleanup", logging=get_settings().get_verbose())
            self._startCleanupTimer()
            self.controller.initDone()
            
            #first thing to do: ask stored peers for their info:
            if len(self._peers) == 0:
                requests = self._peers.initPeersFromFile()
                self.call_request_info(requests)
            
            while self.running:
                try:
                    data, addr = s.recvfrom(1024)
                    ip = unicode(addr[0])
                    
                    log_debug(u"Incoming event from %s: %s" % (ip, convert_string(data)))
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

                    # check if we know this peer          
                    isNewPeer = self._peers.getPeerInfo(pIP=ip) == None          
                    if isNewPeer and self._should_call_info_on_event(data):
                        #this is a new member - we ask for info right away
                        self.call_request_info([ip])
                    
                    self._handle_event(data, ip, time(), isNewPeer, False)
                except socket.timeout:
                    
                    if len(self._peers) > 1:                     
                        if is_in_broadcast_mode:
                            is_in_broadcast_mode = False
                            log_warning("ending broadcast")       
                    else:
                        if not self._disable_broadcast:
                            if not is_in_broadcast_mode:
                                is_in_broadcast_mode = True
                                log_warning("seems like you are alone - broadcasting for others")
                            self._broadcast()
                except socket.error as e:
                    if e.errno != errno.EINTR:
                        raise
        except socket.error as e:
            # socket error messages may contain special characters, which leads to crashes on old python versions
            log_error(u"stopping lunchinator because of socket error:", convert_string(str(e)))
        except KeyboardInterrupt:
            log_info("Received keyboard interrupt, stopping.")
        except:
            log_exception("stopping - Critical error: %s" % str(sys.exc_info())) 
        finally: 
            self.running = False
            try:
                #make sure to close the cleanup thread first
                with self._cleanupLock:
                    self._cleanupTimer.cancel()
                
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

    def perform_call(self, msg, peerIDs, peerIPs):
        """Only the controller should invoke this method -> Called from main thread
        both peerIDs and peerIPs should be sets
        Used also by start_lunchinator to send messages without initializing
        the whole lunch server."""     
        msg = convert_string(msg)
        target = []
        
        if len(peerIDs) == 0 and len(peerIPs) == 0:
            target = self._peers.getPeerIPs()
        else:
            target = peerIPs
            for pID in peerIDs:
                pIPs = self._peers.getPeerIPs(pID=pID)
                if len(pIPs):
                    target = target.union(pIPs)
                else:
                    log_warning("While calling: I do not know a peer with ID %s, ignoring " % pID)
    
        if 0 == len(target):            
            log_error("Cannot send message, there is no peer given or none found")
            
        if self.has_gui() and \
           get_settings().get_warn_if_members_not_ready() and \
           not msg.startswith(u"HELO") and \
           get_settings().get_lunch_trigger().upper() in msg.upper():
            # check if everyone is ready
            notReadyMembers = [self._peers.getPeerName(pID=peerID) for peerID in peerIDs if not self._peers.isPeerReady(pID=peerID)]
            
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
            
    """ ---------------------- PRIVATE -------------------------------- """
    
    def _startCleanupTimer(self):
        self._cleanupTimer = Timer(30, self._cleanup)
        self._cleanupTimer.start()
    
    def _cleanup(self):
        with self._cleanupLock:
            if not self.running:
                return
            log_debug("clean up thread runs")
            try:
                # it's time to announce my name again and switch the master
                self.call("HELO " + get_settings().get_user_name(), peerIPs=self._peers.getPeerIPs())
                self.call_request_dict()
        
                # clean up peers
                self._peers.removeInactive()            
                self._remove_timed_out_queues()
                self._cleanup_cached_messages()
            except:
                log_exception("Something went wrong in the lunch interval thread")
            self._startCleanupTimer()
    
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
        
        try:
            if getPlatform() == PLATFORM_LINUX:
                info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.linux_distribution())
            elif getPlatform() == PLATFORM_WINDOWS:
                info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.win32_ver())
            elif getPlatform() == PLATFORM_MAC:
                info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.mac_ver())
        except:
            log_exception("Error generating OS version string")
            
        if get_settings().get_next_lunch_begin():
            info_d[u"next_lunch_begin"] = get_settings().get_next_lunch_begin()
        if get_settings().get_next_lunch_end():
            info_d[u"next_lunch_end"] = get_settings().get_next_lunch_end()
        self.controller.extendMemberInfo(info_d)
        return json.dumps(info_d)      
    
    def _enqueue_event(self, data, ip, eventTime):
        log_debug("Peer of IP %s is unknown, enqueuing message" % ip)
        
        with self.message_queues_lock:
            if ip in self._message_queues:
                queue = self._message_queues[ip]
            else:
                queue = (time(), [])
            
            queue[1].append((eventTime, data))
            self._message_queues[ip] = queue
        
    def _process_queued_messages(self, ip):
        with self.message_queues_lock:
            if ip in self._message_queues:
                if len(self._message_queues[ip][1]) > 0:
                    log_debug("Processing enqueued messages of IP", ip)
                for eventTime, data in self._message_queues[ip][1]:
                    self._handle_event(data, ip, eventTime, newPeer=False, fromQueue=True)
                del self._message_queues[ip]
    
    def _remove_timed_out_queues(self):
        with self.message_queues_lock:
            for ip in set(self._message_queues.keys()):
                if time() - self._message_queues[ip][0] > get_settings().get_peer_timeout():
                    log_debug("Removing queued messages from IP", ip)
                    del self._message_queues[ip]
    
    def _should_call_info_on_event(self, data):
        return not data.startswith("HELO_REQUEST_INFO") and \
               not data.startswith("HELO_INFO") and \
               not data.startswith("HELO_REQUEST_DICT")
    
    def _cache_message(self, peerID, ip, data, eventTime):
        with self.cached_messages_lock:
            if peerID in self._last_messages:
                lastMessages = self._last_messages[peerID]
            else:
                lastMessages = deque()
            lastMessages.append((eventTime, ip, data))
            self._last_messages[peerID] = lastMessages
        
    def _is_message_duplicate(self, peerID, ip, data):
        # with a high probability, the message is a duplicate if it comes
        # from the same ID but from a different IP.
        
        with self.cached_messages_lock:
            if peerID in self._last_messages:
                for _eventTime, old_ip, old_data in self._last_messages[peerID]:
                    if ip != old_ip and data == old_data:
                        return True
        return False
    
    def _cleanup_cached_messages(self):        
        with self.cached_messages_lock:
            curTime = time()
            for queue in self._last_messages.itervalues():
                while len(queue) > 0 and curTime - queue[0][0] > get_settings().get_message_cache_timeout():
                    queue.popleft()
        
    def _handle_event(self, data, ip, eventTime, newPeer, fromQueue):
        # if there is no HELO in the beginning, it's just a message and 
        # we handle it, if the peer is in our group
        if not data.startswith("HELO"):
            # only process message if we know the peer
            if newPeer:
                self._enqueue_event(data, ip, eventTime)
            else:
                peerID = self._peers.getPeerID(pIP=ip)
                if self._peers.isMember(pID=peerID):
                    if self._is_message_duplicate(peerID, ip, data):
                        log_debug("Dropping duplicate message from peer", peerID)
                        return
                    try:
                        self.getController().processMessage(data, ip, eventTime, newPeer, fromQueue)
                        self._cache_message(peerID, ip, data, eventTime)
                    except:
                        log_exception("Error while handling incoming message from %s: %s" % (ip, data))
                else:
                    log_debug("Dropped a message from %s: %s" % (ip, data))
            return
        
        cmd = u""
        value = u""
        try:
            # commands must always have additional info:
            (cmd, value) = data.split(" ", 1)
        except:
            log_error("Command of %s has no payload: %s" % (ip, data))
        
        # if this packet has info about the peer, we record it and
        # are done. These events are always processed immediately and
        # not enqueued.
        if self._handle_structure_event(ip, cmd, value, newPeer):
            # now it's the plugins' turn:
            self.controller.processEvent(cmd, value, ip, eventTime, False, False)
            return
                            
        try:
            if newPeer:
                self._enqueue_event(data, ip, eventTime)
                
            self._handle_incoming_event(ip, cmd, value, newPeer, fromQueue)
            # now it's the plugins' turn:
            self.controller.processEvent(cmd, value, ip, eventTime, newPeer, fromQueue)
        except:
            log_exception("Unexpected error while handling event from group member %s call: %s" % (ip, str(sys.exc_info())))
            log_critical("The data received was: %s" % data)
    
    def _handle_structure_event(self, ip, cmd, value, newPeer):
        r_value = True
        
        if cmd == "HELO_INFO":
            self._peers.updatePeerInfoByIP(ip, json.loads(value))
            if newPeer:
                self._process_queued_messages(ip)
            
        elif cmd == "HELO_REQUEST_INFO":
            self._peers.updatePeerInfoByIP(ip, json.loads(value))
            self.call_info()
            if newPeer:
                self._process_queued_messages(ip)
        
        elif cmd == "HELO_REQUEST_DICT":
            self._peers.updatePeerInfoByIP(ip, json.loads(value))   
            self.call_dict(ip)           
            if newPeer:
                self._process_queued_messages(ip)

        elif cmd == "HELO_DICT":
            # the master send me the list of _members - yeah
            ext_members = json.loads(value)
            # add every entry and assume, the member is in my group
            for m_ip, _m_name in ext_members.iteritems():
                if not self._peers.getPeerInfo(pIP=m_ip):
                    #this is a new peer - ask for info right away
                    self.call_request_info([m_ip])

        elif cmd == "HELO_LEAVE":
            #the peer tells me that he leaves, I'll remove all of his IPs
            pID = self._peers.getPeerID(pIP=ip)
            self._peers.removePeer(pID)
            
        elif cmd == "HELO":
            # this is just a ping with the members name
            if not self._peers.getPeerInfo(pIP=ip):
                #this is a new peer - ask for info right away
                self.call_request_info([ip])
            
        else:
            r_value = False 
            
        return r_value

    def requets_avatar(self, ip): 
        info = self._peers.getPeerInfo(pIP=ip)
        if info and u"avatar" in info and not os.path.exists(os.path.join(get_settings().get_avatar_dir(), info[u"avatar"])):
            self.call("HELO_REQUEST_AVATAR " + str(self.controller.getOpenTCPPort(ip)), peerIPs=[ip])  
            return True
        return False   
      
            
    def _handle_incoming_event(self, ip, cmd, value, newPeer, _fromQueue):
        # todo: maybe from here on this should be in plugins?
        
        # I don't see any reason to process these events for unknown peers.
        if newPeer:
            return
        
        if cmd == "HELO_AVATAR":
            # someone wants to send me his pic via TCP
            values = value.split()
            file_size = int(values[0].strip())
            tcp_port = 0  # 0 means we must guess the port
            if len(values) > 1:
                tcp_port = int(values[1].strip())
            file_name = ""
            info = self._peers.getPeerInfo(pIP=ip)
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
                self.call("HELO_AVATAR %s" % fileSize, peerIPs = [ip])
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
            self.call("HELO_LOGFILE_TGZ %d %d" % (fileSize, other_tcp_port), peerIPs=[ip])
            self.controller.sendFile(ip, fileToSend.getvalue(), other_tcp_port, True)      
            
    def _finish(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"), "Stopping the lunch notifier service")
        self._peers.finish()
        if self._messages:
            self._messages.finish()
        if self._peerNames:
            self._peerNames.finish()
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
