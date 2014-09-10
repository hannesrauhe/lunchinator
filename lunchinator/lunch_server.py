#!/usr/bin/python
# coding=utf-8

import socket, sys, os, json, contextlib, tarfile, platform, random
from time import strftime, localtime, time
from cStringIO import StringIO

from lunchinator.log import getCoreLogger
from lunchinator.lunch_socket import lunchSocket, splitCall
from lunchinator import get_settings, convert_string, get_notification_center, lunchinator_has_gui
from lunchinator.logging_mutex import loggingMutex
from collections import deque
from threading import Timer
from functools import partial

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
            
        #TODO: Plugin init cannot be done in controller constructor because the GUI has to be ready
        #separation of gui Plugins necessary - but how *sigh*? 
        if get_settings().get_plugins_enabled():
            self.controller.initPlugins()
            from lunchinator.messages import Messages
            self._messages = Messages(logging=get_settings().get_verbose())
        else:
            self._messages = None
             
        from lunchinator.lunch_peers import LunchPeers
        self._peers = LunchPeers()
        get_notification_center().connectPeerUpdated(self._peers._alertIfIPnotMyself)
            
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
            peers_dict[pIP] = self._peers.getRealPeerName(pIP=pIP)
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
        peerIPs = self._peers.getPeerIPs() 
        self.call("HELO_LEAVE Changing Group")
        self._peers.removeMembersByIP()
        self.call_request_info(peerIPs) #call stored peerIPs, otherwise I forget myself after the Leave Call
               
    def get_messages(self):
        return self._messages
    
    def is_running(self):
        return self.running
        
    def set_disable_broadcast(self, disable):
        self._disable_broadcast = disable
        
    def get_disable_broadcast(self):
        return self._disable_broadcast
        
    def getLunchPeers(self):
        return self._peers 
    
    def getController(self):
        return self.controller

    def start_server(self):
        '''listening method - should be started in its own thread''' 
        
        getCoreLogger().info("%s - Starting the lunch notifier service", strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"))
        
        self.my_master = -1  # the peer i use as master
        
        is_in_broadcast_mode = False
        
        self._recv_socket = lunchSocket(self._peers)
        try: 
            self._recv_socket.bind()
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
                    xmsg, ip = self._recv_socket.recv()
                    try:
                        plainMsg = xmsg.getPlainMessage()
                    except:
                        getCoreLogger().exception("There was an error when trying to parse a message from %s", ip)
                        continue
                     
                    # check for local address: only stop command allowed, else ignore
                    if ip.startswith("127."):
                        if xmsg.getCommand() == "STOP":
                            getCoreLogger().info("Got Stop Command from localhost: %s", plainMsg)
                            self.running = False
                            self.exitCode = EXIT_CODE_STOP
                        continue
                    
                    # first we save the timestamp of this contact, no matter what
                    self._peers.seenIP(ip)

                    # check if we know this peer          
                    isNewPeer = self._peers.getPeerInfo(pIP=ip) == None          
                    if isNewPeer and self._should_call_info_on_event(plainMsg):
                        #this is a new member - we ask for info right away
                        self.call_request_info([ip])
                    
                    self._handle_event(xmsg, ip, time(), isNewPeer, False)
                except splitCall as e:
                    getCoreLogger().debug(e.value)
                except socket.timeout:                    
                    if len(self._peers) > 1:                     
                        if is_in_broadcast_mode:
                            is_in_broadcast_mode = False
                            getCoreLogger().info("ending broadcast")       
                    else:
                        if not self._disable_broadcast:
                            if not is_in_broadcast_mode:
                                is_in_broadcast_mode = True
                                getCoreLogger().info("seems like you are alone - broadcasting for others")
                            s_broad = lunchSocket(self._peers)
                            s_broad.broadcast('HELO_REQUEST_INFO ' + self._build_info_string())
                            s_broad.close()
                            #forgotten peers may be on file
                            requests = self._peers.initPeersFromFile()
                            self.call_request_info(requests)
                            
        except socket.error as e:
            # socket error messages may contain special characters, which leads to crashes on old python versions
            getCoreLogger().error(u"stopping lunchinator because of socket error: %s", convert_string(str(e)))
        except KeyboardInterrupt:
            getCoreLogger().info("Received keyboard interrupt, stopping.")
        except:
            getCoreLogger().exception("stopping - Critical error: %s", str(sys.exc_info())) 
        finally: 
            self.running = False
            try:
                #make sure to close the cleanup thread first
                with self._cleanupLock:
                    self._cleanupTimer.cancel()
                
                self.call("HELO_LEAVE bye")
                self._recv_socket.close()
                self._recv_socket = None 
            except:
                getCoreLogger().warning("Wasn't able to send the leave call and close the socket...")
            self._finish()
            
    def stop_server(self, stop_any=False):
        '''this stops a running server thread
        Usually this will not do anything if there is no running thread within the process
        
        @param: stop_any if true it will send a stop call in case another instance has to be stopped
        '''
        
        if stop_any or self.running:
            self.perform_call("HELO_STOP shutdown", peerIPs=set([u"127.0.0.1"]), peerIDs=set())
            # Just in case the call does not reach the socket:
            self.running = False
        else:
            getCoreLogger().warning("There is no running server to stop")

    def perform_call(self, msg, peerIDs, peerIPs):
        """Only the controller should invoke this method -> Called from main thread
        both peerIDs and peerIPs should be sets
        Used also by start_lunchinator to send messages without initializing
        the whole lunch server."""     
        msg = convert_string(msg) # TODO no unicode here?
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
                    getCoreLogger().warning("While calling: I do not know a peer with ID %s, ignoring ", pID)
    
        if 0 == len(target):            
            getCoreLogger().warning("Cannot send message (%s), there is no peer given or none found", msg)
            
        if lunchinator_has_gui() and \
           get_settings().get_warn_if_members_not_ready() and \
           not msg.startswith(u"HELO") and \
           get_settings().get_lunch_trigger().upper() in msg.upper():
            # check if everyone is ready
            notReadyMembers = [self._peers.getDisplayedPeerName(pID=peerID) for peerID in peerIDs if not self._peers.isPeerReady(pID=peerID)]
            
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
                                                 QMessageBox.Yes | QMessageBox.No,
                                                 QMessageBox.No)
                    if result == QMessageBox.No:
                        return
                except ImportError:
                    print warn

        i = 0
        s = lunchSocket(self._peers)
        try:      
            for ip in target:
                try:
                    short = msg if len(msg)<15 else msg[:14]+"..."
                    getCoreLogger().debug("Sending %s to %s", short, ip.strip())
                    s.sendto(msg, ip.strip())
                    i += 1
                except Exception as e:
                    getCoreLogger().warning("The following message could not be delivered to %s: %s", ip, msg, exc_info=1)
        finally:
            s.close() 
        return i
            
    """ ---------------------- PRIVATE -------------------------------- """
    
    def _startCleanupTimer(self):
        interval = get_settings().get_peer_timeout() / 2
        interval = 30 if interval>30 else interval
        self._cleanupTimer = Timer(interval, self._cleanup)
        self._cleanupTimer.start()
    
    def _cleanup(self):
        with self._cleanupLock:
            if not self.running:
                return
            getCoreLogger().debug("clean up thread runs")
            try:
                # it's time to announce my name again and switch the master
                self.call("HELO " + get_settings().get_user_name(), peerIPs=self._peers.getPeerIPs())
                self.call_request_dict()
        
                # clean up peers
                self._peers.removeInactive()            
                self._remove_timed_out_queues()
                self._cleanup_cached_messages()
                self._recv_socket.drop_incomplete_messages()
            except:
                getCoreLogger().exception("Something went wrong in the lunch interval thread")
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
                   u"platform": sys.platform}
        
        try:
            if getPlatform() == PLATFORM_LINUX:
                info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.linux_distribution())
            elif getPlatform() == PLATFORM_WINDOWS:
                info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.win32_ver())
            elif getPlatform() == PLATFORM_MAC:
                info_d[u"os"] = u" ".join(aString if type(aString) in (str, unicode) else "[%s]" % " ".join(aString) for aString in platform.mac_ver())
        except:
            getCoreLogger().exception("Error generating OS version string")
            
        if get_settings().get_next_lunch_begin():
            info_d[u"next_lunch_begin"] = get_settings().get_next_lunch_begin()
        if get_settings().get_next_lunch_end():
            info_d[u"next_lunch_end"] = get_settings().get_next_lunch_end()
        self.controller.extendMemberInfo(info_d)
        return json.dumps(info_d)      
    
    def _enqueue_event(self, xmsg, ip, eventTime):
        getCoreLogger().debug("Peer of IP %s is unknown, enqueuing message", ip)
        
        with self.message_queues_lock:
            if ip in self._message_queues:
                queue = self._message_queues[ip]
            else:
                queue = (time(), [])
            
            queue[1].append((eventTime, xmsg))
            self._message_queues[ip] = queue
        
    def _process_queued_messages(self, ip):
        with self.message_queues_lock:
            if ip in self._message_queues:
                if len(self._message_queues[ip][1]) > 0:
                    getCoreLogger().debug("Processing enqueued messages of IP %s", ip)
                for eventTime, xmsg in self._message_queues[ip][1]:
                    self._handle_event(xmsg, ip, eventTime, newPeer=False, fromQueue=True)
                del self._message_queues[ip]
    
    def _remove_timed_out_queues(self):
        with self.message_queues_lock:
            for ip in set(self._message_queues.keys()):
                if time() - self._message_queues[ip][0] > get_settings().get_peer_timeout():
                    getCoreLogger().debug("Removing queued messages from IP %s", ip)
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
        
    def _handle_event(self, xmsg, ip, eventTime, newPeer, fromQueue):
        """ processes a call received by the lunch_socket
        
        @type xmsg: extMessageIncoming
        @type ip: unicode
        @type eventTime: float
        @type newPeer: boolean
        @type fromQueue: boolean 
        """
        data = xmsg.getPlainMessage()
        # if there is no HELO in the beginning, it's just a message and 
        # we handle it, if the peer is in our group
        if not xmsg.isCommand():
            # only process message if we know the peer
            if newPeer:
                self._enqueue_event(xmsg, ip, eventTime)
            else:
                peerID = self._peers.getPeerID(pIP=ip)
                if self._peers.isMember(pID=peerID):
                    if self._is_message_duplicate(peerID, ip, data):
                        getCoreLogger().debug("Dropping duplicate message from peer %s", peerID)
                        return
                    try:
                        self.getController().processMessage(xmsg, ip, eventTime, newPeer, fromQueue)
                        self._cache_message(peerID, ip, data, eventTime)
                    except:
                        getCoreLogger().exception("Error while handling incoming message from %s: %s", ip, data)
                else:
                    getCoreLogger().debug("Dropped a message from %s: %s", ip, data)
            return
        
        
        # if this packet has info about the peer, we record it and
        # are done. These events are always processed immediately and
        # not enqueued.
        if self._handle_structure_event(ip, xmsg, newPeer):
            # now it's the plugins' turn:
            self.controller.processEvent(xmsg, ip, eventTime, False, False)
            return
                            
        try:
            if newPeer:
                self._enqueue_event(xmsg, ip, eventTime)
                
            self._handle_core_event(ip, xmsg, newPeer, fromQueue)
            # now it's the plugins' turn:
            self.controller.processEvent(xmsg, ip, eventTime, newPeer, fromQueue)
        except:
            getCoreLogger().exception("Unexpected error while handling event from group member %s call: %s", ip, str(sys.exc_info()))
            getCoreLogger().critical("The data received was: %s", data)
    
    def _updateInfoDict(self, ip, value):
        self._peers.updatePeerInfoByIP(ip, json.loads(value))
        if self._peers.getAvatarOutdated(pIP=ip):
            self.request_avatar(ip)
    
    def _handle_structure_event(self, ip, xmsg, newPeer):
        """ handle events that influence peer list and info
        @type ip: unicode 
        @type xmsg: extMessageIncoming 
        @type newPeer: bool 
        """
        r_value = True
        
        cmd = xmsg.getCommand()
        value = xmsg.getCommandPayload()
        
        if cmd == "INFO":
            self._updateInfoDict(ip, value)
            if newPeer:
                self._process_queued_messages(ip)
            
        elif cmd == "REQUEST_INFO":
            self._updateInfoDict(ip, value)
            self.call_info()
            if newPeer:
                self._process_queued_messages(ip)
        
        elif cmd == "REQUEST_DICT":
            self._updateInfoDict(ip, value)
            self.call_dict(ip)           
            if newPeer:
                self._process_queued_messages(ip)

        elif cmd == "DICT":
            # the master send me the list of _members - yeah
            ext_members = json.loads(value)
            # add every entry and assume, the member is in my group
            for m_ip, _m_name in ext_members.iteritems():
                if not self._peers.getPeerInfo(pIP=m_ip):
                    #this is a new peer - ask for info right away
                    self.call_request_info([m_ip])

        elif cmd == "LEAVE":
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

    def request_avatar(self, ip): 
        info = self._peers.getPeerInfo(pIP=ip)
        if info and u"avatar" in info and not os.path.exists(os.path.join(get_settings().get_avatar_dir(), info[u"avatar"])):
            self.call("HELO_REQUEST_AVATAR " + str(self.controller.getOpenTCPPort(ip)), peerIPs=[ip])  
            return True
        return False   
      
    def _handle_core_event(self, ip, xmsg, newPeer, _fromQueue):
        ''' handles cmds that are not necessary for peer discovery but should work without plugins 
        '''
        
        # I don't see any reason to process these events for unknown peers.
        if newPeer:
            return
        cmd = xmsg.getCommand()
        value = xmsg.getCommandPayload()
        
        if cmd == "AVATAR":
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
                getCoreLogger().error("%s tried to send his avatar, but I don't know where to save it", ip)
            
            if len(file_name):
                pID = self._peers.getPeerID(pIP=ip)
                getCoreLogger().info("Receiving avatar from peer with ID %s, IP %s", pID, ip)
                self.controller.receiveFile(ip,
                                            file_size,
                                            file_name,
                                            tcp_port,
                                            successFunc=partial(get_notification_center().emitAvatarChanged,
                                                                pID,
                                                                info[u"avatar"]))
            
        elif cmd == "REQUEST_AVATAR":
            # someone wants my pic 
            other_tcp_port = get_settings().get_tcp_port()
            
            try:                    
                other_tcp_port = int(value.strip())
            except:
                getCoreLogger().exception("%s requested avatar, I could not parse the port from value %s, using standard %d", str(ip), str(value), other_tcp_port)
                
            fileToSend = os.path.join(get_settings().get_avatar_dir(), get_settings().get_avatar_file())
            if os.path.exists(fileToSend):
                fileSize = os.path.getsize(fileToSend)
                getCoreLogger().info("Sending file of size %d to %s : %d", fileSize, str(ip), other_tcp_port)
                self.call("HELO_AVATAR %s %s" % (fileSize, other_tcp_port), peerIPs = [ip])
                self.controller.sendFile(ip, fileToSend, other_tcp_port)
            else:
                # TODO should this be an error? If somebody deletes the avatar file, it should be reset silently -> warning
                getCoreLogger().error("Want to send file %s, but cannot find it", fileToSend)   
            
        elif cmd == "REQUEST_LOGFILE":
            # someone wants my logfile 
            other_tcp_port = get_settings().get_tcp_port()
            try:                
                (oport, _) = value.split(" ", 1)    
                other_tcp_port = int(oport.strip())
            except:
                getCoreLogger().exception("%s requested the logfile, I could not parse the port and number from value %s, using standard %d and logfile 0", str(ip), str(value), other_tcp_port)
            
            fileToSend = StringIO()
            with contextlib.closing(tarfile.open(mode='w:gz', fileobj=fileToSend)) as tarWriter:
                if os.path.exists(get_settings().log_file()):
                    tarWriter.add(get_settings().log_file(), arcname="0.log")
                logIndex = 1
                while os.path.exists("%s.%d" % (get_settings().log_file(), logIndex)):
                    tarWriter.add("%s.%d" % (get_settings().log_file(), logIndex), arcname="%d.log" % logIndex)
                    logIndex = logIndex + 1
            
            fileSize = fileToSend.tell()
            getCoreLogger().info("Sending file of size %d to %s : %d", fileSize, str(ip), other_tcp_port)
            self.call("HELO_LOGFILE_TGZ %d %d" % (fileSize, other_tcp_port), peerIPs=[ip])
            self.controller.sendFile(ip, fileToSend.getvalue(), other_tcp_port, True)      
            
    def _finish(self):
        getCoreLogger().info("%s - Stopping the lunch notifier service", strftime("%a, %d %b %Y %H:%M:%S", localtime()).decode("utf-8"))
        self._peers.finish()
        if self._messages:
            self._messages.finish()
        self.controller.serverStopped(self.exitCode)
        
    def has_gui(self):
        """ returns if a GUI and qt is present
        @deprecated: use lunchinator.lunchinator_has_gui() instead
        """
        return lunchinator_has_gui()
