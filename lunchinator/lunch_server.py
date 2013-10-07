#!/usr/bin/python
from iface_plugins import iface_called_plugin, iface_database_plugin, iface_general_plugin, iface_gui_plugin, PluginManagerSingleton
from time import strftime, localtime, time, mktime
import socket,sys,os,json,codecs,contextlib
from threading import Lock
from cStringIO import StringIO

from yapsy.ConfigurablePluginManager import ConfigurablePluginManager
from lunchinator import log_debug, log_info, log_critical, get_settings, log_exception, log_error, log_warning
import tarfile

EXIT_CODE_UPDATE = 2
EXIT_CODE_STOP = 3
        
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
        self.peer_nr=0 #the number of the peer i contacted to be my master
        self.mute_time_until=0
        self.last_messages = []
        self.members = []
        self.member_timeout = {}
        self.member_info = {}
        self.plugin_manager = None
        self.no_updates = False
        self.own_ip = "0.0.0.0"
        self.messagesLock = Lock()
        self.membersLock = Lock()
        self.shared_dict = {} #for plugins
        self.dontSendTo = set()
        
        self.exitCode = 0  
        
        
    """ -------------------------- CALLED FROM MAIN THREAD -------------------------------- """
        
    """Initialize Lunch Server with a specific controller"""
    def initialize(self, controller = None):
        if self.initialized:
            return
        if controller != None:
            self.controller = controller
        else:
            from lunchinator.lunch_server_controller import LunchServerController
            self.controller = LunchServerController()
        
        self._read_config()
        
        PluginManagerSingleton.setBehaviour([
            ConfigurablePluginManager,
        ])
        self.plugin_manager = PluginManagerSingleton.get()
        self.plugin_manager.app = self
        self.plugin_manager.setConfigParser(get_settings().get_config_file(),get_settings().write_config_to_hd)
        self.plugin_manager.setPluginPlaces(get_settings().get_plugin_dirs())
        if self.get_plugins_enabled():
            categoriesFilter = {
               "general" : iface_general_plugin,
               "called" : iface_called_plugin,
               "gui" : iface_gui_plugin,
               "db" : iface_database_plugin
               }
            self.plugin_manager.setCategoriesFilter(categoriesFilter) 
        
        if self.get_plugins_enabled():
            try:
                self.plugin_manager.collectPlugins()
            except:
                log_exception("problem when loading plugin")
            
            #always load these plugins
            self.plugin_manager.activatePluginByName("General Settings", "general") 
            self.plugin_manager.activatePluginByName("Notify", "called") 
        else:
            log_info("lunchinator initialised without plugins")  
        self.initialized = True
        
    def getDBConnection(self,db_name=None):
        if None!=db_name and ""!=db_name:
            pluginInfo = self.plugin_manager.getPluginByName(db_name, "db")
            if pluginInfo and pluginInfo.plugin_object.is_activated:
                return pluginInfo.plugin_object
            log_error("No DB connection for %s available, falling back to default"%db_name)
        
        for pluginInfo in self.plugin_manager.getPluginsOfCategory("db"):
            if pluginInfo.plugin_object.is_activated:
                return pluginInfo.plugin_object
        log_error("No DB Connection available - activate a db plugin and check settings")
        return None
    
    """ -------------------------- CALLED FROM ARBITRARY THREAD -------------------------- """
    
    
    '''listening method - should be started in its own thread'''    
    def start_server(self):
        self.initialize()
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Starting the lunch notifier service")
        self.running = True
        self.my_master=-1 #the peer i use as master
        announce_name=0 #how often did I announce my name        
            
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #getting your IP address is hard...:
        socket.gethostbyname(socket.gethostname()) #may return something like 127.* or 0.*
        try:
            if self.own_ip.startswith("127.") or self.own_ip.startswith("0."):
                self.own_ip = socket.gethostbyname(socket.getfqdn())        
        except:
            log_exception("Exception trying to determine own IP")
        if self.own_ip.startswith("127.") or self.own_ip.startswith("0."):
            log_warning("IP address could not be determined, so I'm using your hostname, some things might not work correctly (e.g., statistics)")
            self.own_ip = socket.gethostname()[:15]
            
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            self.controller.initDone()
            while self.running:
                if self.new_msg and (time()-mktime(self.getMessage(0)[0]))>(get_settings().get_reset_icon_time()*60):
                    self.new_msg=False
                try:
                    daten, addr = s.recvfrom(1024)
                    daten = daten.decode('utf-8')
                    ip = unicode(addr[0])
                    if not ip.startswith("127."):
                        self.member_timeout[ip]=time()
                        if not ip in self.members:
                            self._append_member(ip, ip)
                        
                    if daten.startswith("HELO"):
                        #simple infrastructure protocol messages starting with HELO''' 
                        self._incoming_event(daten, ip)                            
                    else:  
                        #simple message                          
                        self._incoming_call(daten,ip)
                except socket.timeout:
                    if len(self.members):
                        if self.my_master==-1:
                            self._call_for_dict()
                        else:
                            if announce_name==10:
                                #it's time to announce my name again and switch the master
                                self.call("HELO "+get_settings().get_user_name())
                                announce_name=0
                                self._remove_inactive_members()
                                self._call_for_dict()
                            else:
                                #just wait for the next time when i have to announce my name
                                announce_name+=1
                        if self.my_master==-1:
                            log_info("no master found yet")
                    else:
                        #TODO: broadcast at this point
                        log_warning("seems like you are alone - no lunch-peer found yet")
                    log_debug("Current Members:", self.members)
        except socket.error as e:
            log_exception("stopping lunchinator because: %s"%(str(e)))
        except:
            log_exception("stopping - Critical error: %s"%str(sys.exc_info())) 
        finally: 
            try:
                self.call("HELO_LEAVE bye")
                s.close()  
            except:
                log_warning("Wasn't able to send the leave call and close the socket...")
            self._finish()
            
    def memberName(self, addr):
        if addr in self.member_info and u'name' in self.member_info[addr]:
            return self.member_info[addr][u'name']
        return addr
    
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
        self.messagesLock.acquire()
        
    def releaseMessages(self):
        self.messagesLock.release()
        
    def lockMembers(self):
        self.membersLock.acquire()
        
    def releaseMembers(self):
        self.membersLock.release()
            
    def getMessages(self):  
        return self.last_messages
    
    def get_members(self):  
        return self.members

    def get_member_timeout(self):  
        return self.member_timeout    
    
    def get_plugins_enabled(self):
        return self._load_plugins
    def set_plugins_enabled(self, enable):
        self._load_plugins = enable
    
    def get_member_info(self):  
        return self.member_info    
    
    def getOwnIP(self):
        return self.own_ip
        
    def call(self,msg,client='',hosts=[]):
        self.initialize()
        
        target = None
        if client:
            # send to client regardless of the dontSendTo state
            target = [client.strip()]
        elif 0==len(hosts):
            target = set(self.members) - self.dontSendTo
        else:
            # send to all specified hosts regardless of the dontSendTo state
            target = set(hosts)
        
        if 0==len(target):
            log_error("Cannot send message, no peers connected, no peer found in members file")

        i = 0
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        try:      
            for ip in target:
                try:
                    log_debug("Sending", msg, "to", ip.strip())
                    s.sendto(msg.encode('utf-8'), (ip.strip(), 50000))
                    i+=1
                except:
                    # only warning message; happens sometimes if the host is not reachable
                    log_warning("Message could not be delivered to %s: %s" % (ip, str(sys.exc_info()[0])))
                    continue
        finally:
            s.close() 
        return i
        
    '''short for the call function above for backward compatibility'''
    def call_all_members(self,msg):        
        self.call(msg)   
            
    """ ---------------------- PRIVATE -------------------------------- """
    
    def _finish(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service")
        self._write_members_to_file()
        self._write_messages_to_file()
        self.controller.serverStopped(self.exitCode)
        
    def _read_config(self):              
        if len(self.members)==0:
            self._init_members_from_file()
        if len(self.last_messages)==0:
            self.last_messages=self._init_messages_from_file()
    
    def _updateMembersDict(self, otherDict, noLocal = True):
        for ip, hostn in otherDict.items():
            if noLocal and ip.startswith('127'):
                continue
            self._append_member(ip, hostn)
            
    def _is_now_in_time_span(self,begin,end):
        try:
            begin_hour,_,begin_min = begin.partition(":")
            end_hour,_,end_min = end.partition(":")
            return localtime()[3]*60+localtime()[4] >= int(begin_hour)*60+int(begin_min) and localtime()[3]*60+localtime()[4] <= int(end_hour)*60+int(end_min)
        except:
            log_exception("don't know how to handle time span %s"%(str(sys.exc_info())))
            return False;
        
    def _memberAppended(self, ip):
        self.controller.memberAppended(ip, self.member_info[ip])
    
    def _memberUpdated(self, ip):
        self.controller.memberUpdated(ip, self.member_info[ip])
    
    def _memberRemoved(self, ip):
        self.controller.memberRemoved(ip)
        
    def _append_member(self, ip, hostn, inform = True):
        # insert name into info dict
        memberInfo = {}
        if ip in self.member_info:
            memberInfo = self.member_info[ip]
        memberInfo[u'name'] = hostn
        
        self.lockMembers()
        try:
            self.member_info[ip] = memberInfo
            
            if not ip in self.members:
                self.members.append(ip)
                if inform:
                    self._memberAppended(ip)
            elif inform:
                self._memberUpdated(ip)
        finally:
            self.releaseMembers()
            
    def _init_members_from_file(self):
        members = []
        if os.path.exists(get_settings().get_members_file()):
            with codecs.open(get_settings().get_members_file(),'r','utf-8') as f:    
                for hostn in f.readlines():
                    hostn = hostn.strip()
                    if len(hostn) == 0:
                        continue
                    try:
                        ip = unicode(socket.gethostbyname(hostn))
                        self._append_member(ip, hostn, False)
                    except:
                        log_warning("cannot find host specified in members_file by %s with name %s"%(get_settings().get_members_file(),hostn))
        return members
    
    def _write_members_to_file(self):
        try:
            if len(self.members)>1:
                with codecs.open(get_settings().get_members_file(),'w','utf-8') as f:
                    f.truncate()
                    for m in self.members:
                        f.write(m+"\n")
        except:
            log_exception("Could not write members to %s"%(get_settings().get_members_file()))
            
    def _init_messages_from_file(self):
        messages = []
        if os.path.exists(get_settings().get_messages_file()):
            try:
                with codecs.open(get_settings().get_messages_file(),'r','utf-8') as f:    
                    tmp_msg = json.load(f)
                    for m in tmp_msg:
                        messages.append([localtime(m[0]),m[1],m[2]])
            except:
                log_exception("Could not read messages file %s,but it seems to exist"%(get_settings().get_messages_file()))
        return messages
    
    def _write_messages_to_file(self):
        try:
            if self.messagesCount()>0:
                with codecs.open(get_settings().get_messages_file(),'w','utf-8') as f:
                    f.truncate()
                    msg = []
                    self.messagesLock.acquire()
                    try:
                        for m in self.last_messages:
                            msg.append([mktime(m[0]),m[1],m[2]])
                    finally:
                        self.messagesLock.release()
                    json.dump(msg,f)
        except:
            log_exception("Could not write messages to %s: %s"%(get_settings().get_messages_file(), sys.exc_info()[0]))    
    
    def _build_info_string(self):
        info_d = {u"avatar": get_settings().get_avatar_file(),
                   u"name": get_settings().get_user_name(),
                   u"next_lunch_begin":get_settings().get_default_lunch_begin(),
                   u"next_lunch_end":get_settings().get_default_lunch_end(),
                   u"version":get_settings().get_version_short(),
                   u"version_commit_count":get_settings().get_commit_count(),
                   u"version_commit_count_plugins":get_settings().get_commit_count_plugins()}
        if get_settings().get_next_lunch_begin():
            info_d[u"next_lunch_begin"] = get_settings().get_next_lunch_begin()
        if get_settings().get_next_lunch_end():
            info_d[u"next_lunch_end"] = get_settings().get_next_lunch_end()
        return json.dumps(info_d)      
        
    def _createMembersDict(self):
        membersDict = {}
        for ip in self.members:
            if ip in self.member_info and u'name' in self.member_info[ip]:
                membersDict[ip] = self.member_info[ip][u'name']
            else:
                membersDict[ip] = ip
        return membersDict
        
    def _incoming_call(self,msg,addr):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        m = self.memberName(addr)
            
        log_info("%s: [%s] %s" % (t,m,msg))
        
        self._insertMessage(mtime,addr,msg)
        self.controller.messagePrepended(mtime,addr,msg)
        self.new_msg = True
        self._write_messages_to_file()
        
        if not msg.startswith("ignore"):
            self.controller.processMessage(msg, addr)
            
            if "lunch" in msg.lower() and self._is_now_in_time_span(get_settings().get_alarm_begin_time(), get_settings().get_alarm_end_time()):
                timenum = mktime(mtime)
                if timenum>self.mute_time_until:
                    self.mute_time_until=timenum+get_settings().get_mute_timeout()
                    self.controller.processLunchCall(msg, addr)
                else:
                    log_debug("messages will not trigger alarm: %s: [%s] %s until %s"%(t,m,msg,strftime("%a, %d %b %Y %H:%M:%S", localtime(self.mute_time_until))))
      
    def _update_member_info(self, ip, newInfo, requestAvatar = True):
        self.lockMembers()
        try:
            self.member_info[ip] = newInfo
        finally:
            self.releaseMembers()
        self._memberUpdated(ip)
        if requestAvatar:
            #Request avatar if not there yet
            if self.member_info[ip].has_key("avatar"):
                if not os.path.exists(get_settings().get_avatar_dir()+"/"+self.member_info[ip]["avatar"]):
                    self.call("HELO_REQUEST_AVATAR "+str(get_settings().get_tcp_port()),client=ip)     
      
    def _incoming_event(self,data,ip):   
        if ip.startswith("127."):
            #stop command is only allowed from localhost :-)
            if data.startswith("HELO_STOP"):
                log_info("Got Stop Command from localhost: %s"%data)
                self.running = False
                self.exitCode = EXIT_CODE_STOP #run_forever script will stop
            elif data.startswith("HELO_UPDATE"):
                self.update_request = True
                if get_settings().get_auto_update_enabled() and not self.no_updates:
                    log_info("local update")
                    self.running = False
                    
                    #new update-script:
                    self.exitCode = EXIT_CODE_UPDATE
                else:
                    log_info("local update issued but updates are disabled")
            #only stop and update command is allowed from localhost, returning here
            return     
                
        try:        
            (cmd, value) = data.split(" ",1)
            if cmd.startswith("HELO_UPDATE"):
                t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                self.update_request = True
                if get_settings().get_auto_update_enabled() and not self.no_updates:
                    log_info("%s: [%s] update"%(t,ip))
                    self.running = False
                    
                    #new update-script:
                    self.exitCode = EXIT_CODE_UPDATE
                else:
                    log_info("%s: %s issued an update but updates are disabled"%( t,ip))
                
            elif cmd.startswith("HELO_REQUEST_DICT"):
                self._update_member_info(ip, json.loads(value))
                self.call("HELO_DICT "+json.dumps(self._createMembersDict()),client=ip)                   
                
            elif cmd.startswith("HELO_DICT"):
                #the master send me the list of members - yeah
                ext_members = json.loads(data.split(" ",1)[1].strip())
                self._updateMembersDict(ext_members)
                if self.my_master==-1:
                    self.call("HELO_REQUEST_INFO "+self._build_info_string())
                    
                self.my_master = ip   
                 
            elif cmd.startswith("HELO_REQUEST_INFO"):
                # TODO @Hannes: why aren't we requesting the avatar here?
                self._update_member_info(ip, json.loads(value), requestAvatar=False)
                self.call("HELO_INFO "+self._build_info_string(),client=ip)
                         
            elif cmd.startswith("HELO_INFO"):
                #someone sends his info
                self._update_member_info(ip, json.loads(value)) 
                                    
            elif cmd.startswith("HELO_LEAVE"):
                #the sender tells me, that he is going
                if ip in self.members:
                    self.lockMembers()
                    try:
                        self.members.remove(ip)
                    finally:
                        self.releaseMembers()
                    self._memberRemoved(ip)
                self.call("HELO_DICT "+json.dumps(self._createMembersDict()),client=ip)
               
            elif cmd.startswith("HELO_AVATAR"):
                #someone wants to send me his pic via TCP
                file_size=int(value.strip())
                file_name=""
                if self.member_info[ip].has_key("avatar"):
                    file_name=get_settings().get_avatar_dir()+os.sep+self.member_info[ip]["avatar"]
                else:
                    log_error("%s tried to send his avatar, but I don't know where to safe it"%(ip))
                
                if len(file_name):
                    log_info("Receiving file of size %d on port %d"%(file_size,get_settings().get_tcp_port()))
                    self.controller.receiveFile(ip,file_size,file_name)
                
            elif cmd.startswith("HELO_REQUEST_AVATAR"):
                #someone wants my pic 
                other_tcp_port = get_settings().get_tcp_port()
                
                try:                    
                    other_tcp_port=int(value.strip())
                except:
                    log_exception("%s requested avatar, I could not parse the port from value %s, using standard %d"%(str(ip),str(value),other_tcp_port))
                    
                fileToSend = get_settings().get_avatar_dir()+"/"+get_settings().get_avatar_file()
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    log_info("Sending file of size %d to %s : %d"%(fileSize,str(ip),other_tcp_port))
                    self.call("HELO_AVATAR "+str(fileSize), ip)
                    self.controller.sendFile(ip,fileToSend, other_tcp_port)
                else:
                    log_error("Want to send file %s, but cannot find it"%(fileToSend))   
                
            elif cmd.startswith("HELO_REQUEST_LOGFILE"):
                #someone wants my logfile 
                other_tcp_port = get_settings().get_tcp_port()
                try:                
                    (oport, _) = value.split(" ",1)    
                    other_tcp_port=int(oport.strip())
                except:
                    log_exception("%s requested the logfile, I could not parse the port and number from value %s, using standard %d and logfile 0"%(str(ip),str(value),other_tcp_port))
                
                fileToSend = StringIO()
                with contextlib.closing(tarfile.open(mode='w:gz', fileobj=fileToSend)) as tarWriter:
                    if os.path.exists(get_settings().get_log_file()):
                        tarWriter.add(get_settings().get_log_file(), arcname="0.log")
                    logIndex = 1
                    while os.path.exists("%s.%d" % (get_settings().get_log_file(), logIndex)):
                        tarWriter.add("%s.%d" % (get_settings().get_log_file(), logIndex), arcname="%d.log" % logIndex)
                        logIndex = logIndex + 1
                
                fileSize = fileToSend.tell()
                log_info("Sending file of size %d to %s : %d"%(fileSize,str(ip),other_tcp_port))
                self.call("HELO_LOGFILE_TGZ %d %d" %(fileSize, other_tcp_port), ip)
                self.controller.sendFile(ip,fileToSend.getvalue(), other_tcp_port, True)
            elif "HELO"==cmd:
                #someone tells me his name
                didKnowMember = ip in self.members
                self._append_member(ip, value) 
                if not didKnowMember:
                    self.call("HELO_INFO "+self._build_info_string(),client=ip)
            else:
                log_info("received unknown command from %s: %s with value %s"%(ip,cmd,value))        
            
            self.controller.processEvent(cmd,value,ip)
        except:
            log_exception("Unexpected error while handling HELO call: %s"%(str(sys.exc_info())))
            log_critical("The data received was: %s"%data)
    
    def _insertMessage(self, mtime,addr,msg):
        self.messagesLock.acquire()
        try:
            self.last_messages.insert(0,[mtime,addr,msg])
        finally:
            self.messagesLock.release()
                    
    def _remove_inactive_members(self):
        try:
            indicesToRemove = []
            for memberIndex, ip in enumerate(self.members):
                if ip in self.member_timeout:
                    if time()-self.member_timeout[ip]>get_settings().get_peer_timeout():
                        indicesToRemove.append(memberIndex)
                else:
                    indicesToRemove.append(memberIndex)
                    
            log_debug("Removing inactive members: %s (%s)" %([self.members[i] for i in indicesToRemove], indicesToRemove))
            for memberIndex in reversed(indicesToRemove):
                self._memberRemoved(self.members[memberIndex])
            self.lockMembers()
            try:
                for memberIndex in reversed(indicesToRemove):
                    del self.members[memberIndex]
            finally:
                self.releaseMembers()
        except:
            log_exception("Something went wrong while trying to clean up the members-table")
            
    '''ask for the dictionary and send over own information'''
    def _call_for_dict(self):
        try:
            if len(self.members)>self.peer_nr:
                self.call("HELO_REQUEST_DICT "+self._build_info_string(),client=self.members[self.peer_nr])
            self.peer_nr=(self.peer_nr+1) % len(self.members)
        except:
            log_exception("Something went wrong while trying to send a call to the new master")
