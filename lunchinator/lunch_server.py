#!/usr/bin/python
from lunch_datathread import *
from iface_plugins import *
from time import strftime, localtime, time, mktime, gmtime
import socket,subprocess,sys,os,ctypes,getpass,json,logging

from yapsy.PluginManager import PluginManagerSingleton
from yapsy.ConfigurablePluginManager import ConfigurablePluginManager
from lunchinator import log_debug, log_info, log_critical, get_settings

EXIT_CODE_UPDATE = 2
EXIT_CODE_STOP = 3
        
class lunch_server(object):
    _instance = None
    
    @classmethod
    def get_singleton_server(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
    
    #TODO: if started with plugins: make sure they are deactivated when destroying lunchinator (destructor anyone?)
    def __init__(self):
        self.running = False
        self.update_request = False
        self.new_msg = False
        self.my_master = -1    
        self.peer_nr=0 #the number of the peer i contacted to be my master
        self.mute_time_until=0
        self.last_messages = []
        self.members = {}
        self.member_timeout = {}
        self.member_info = {}
        self.plugin_manager = None
        self.no_updates = False
        self.with_plugins = True
        self.own_ip = "0.0.0.0"
        
        self.exitCode = 0  
        self.read_config()
        
        PluginManagerSingleton.setBehaviour([
            ConfigurablePluginManager,
        ])
        self.plugin_manager = PluginManagerSingleton.get()
        #logging.getLogger('yapsy').setLevel(logging.DEBUG)
        self.plugin_manager.app = self
        self.plugin_manager.setConfigParser(get_settings().config_file,get_settings().write_config_to_hd)
        self.plugin_manager.setPluginPlaces(get_settings().plugin_dirs)
        self.plugin_manager.setCategoriesFilter({
           "general" : iface_general_plugin,
           "called" : iface_called_plugin,
           "gui" : iface_gui_plugin,
           "db" : iface_database_plugin
           }) 
        self.init_done = threading.Event()
        self.shared_dict = {} #for plugins
        
    def getDBConnection(self,conn_name):
        conn=None
        for pluginInfo in self.plugin_manager.getPluginsOfCategory("db"):
            try:
                if conn_name in pluginInfo.plugin_object.get_available_connections():
                    conn=pluginInfo.plugin_object
                    conn.switch_connection(conn_name)                    
                    break
            except:
                log_exception("plugin error in %s while choosing DB Connection %s: %s"%(pluginInfo.name, conn_name, str(sys.exc_info())))
        return conn
    
    def getOwnIP(self):
        return self.own_ip
        
    def is_now_in_time_span(self,begin,end):
        try:
            begin_hour,_,begin_min = begin.partition(":")
            end_hour,_,end_min = end.partition(":")
            return localtime()[3]*60+localtime()[4] >= int(begin_hour)*60+int(begin_min) and localtime()[3]*60+localtime()[4] <= int(end_hour)*60+int(end_min)
        except:
            log_exception("don't know how to handle time span %s"%(str(sys.exc_info())))
            return False;
        
    def call(self,msg,client='',hosts={}):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        i=0
        if client:
            log_debug("Sending message %s to %s"%(msg,client))
            try:
                s.sendto(msg, (client.strip(), 50000)) 
                i+=1
            except:
                log_exception("Exception while sending msg %s to %s: %s"%(msg,client, str(sys.exc_info()[0])))
        elif 0==len(hosts):
            members = self.members
            if 0==len(members):
                members = self.init_members_from_file()            
            if 0==len(members):
                log_error("Cannot send message, no peers connected, no peer found in members file")
                return 0
            log_debug("Sending message %s to %s"%(msg,str(members)))
            for ip,name in members.items():
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    i+=1
                except:
                    log_exception("Exception while sending msg %s to %s: %s"%(msg,client, str(sys.exc_info()[0])))
                    continue        
        else:
            log_debug("Sending message %s to %s",msg,str(hosts))
            for ip,name in hosts.items():
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    i+=1
                except:
                    log_exception("Exception while sending msg %s to %s: %s"%(msg,client, str(sys.exc_info()[0])))
                    continue
        
        s.close() 
        return i
        
    '''short for the call function above for backward compatibility'''
    def call_all_members(self,msg):        
        self.call(msg,hosts=self.members)   
        
        
    '''will be called every ten seconds'''
    def read_config(self):              
        if len(self.members)==0:
            self.members=self.init_members_from_file()
        if len(self.last_messages)==0:
            self.last_messages=self.init_messages_from_file()
            
            
    def init_members_from_file(self):
        members = {}
        if os.path.exists(get_settings().members_file):
            f = open(get_settings().members_file,'r')    
            for hostn in f.readlines():
                try:
                    members[socket.gethostbyname(hostn.strip())]=hostn.strip()
                except:
                    log_warning("cannot find host specified in members_file by %s with name %s"%(get_settings().members_file,hostn))
            f.close()
        return members
    
    def write_members_to_file(self):
        try:
            if len(self.members)>1:
                f = open(get_settings().members_file,'w')
                f.truncate()
                for m in self.members.keys():
                    f.write(m+"\n")
                f.close();
        except:
            log_exception("Could not write members to %s"%(get_settings().members_file))
            
    def init_messages_from_file(self):
        messages = []
        if os.path.exists(get_settings().messages_file):
            try:
                f = open(get_settings().messages_file,'r')    
                tmp_msg = json.load(f)
                for m in tmp_msg:
                    messages.append([localtime(m[0]),m[1],m[2]])
                f.close()
            except:
                log_exception("Could not read messages file %s,but it seems to exist"%(get_settings().messages_file))
        return messages
    
    def write_messages_to_file(self):
        try:
            if len(self.last_messages)>0:
                f = open(get_settings().messages_file,'w')
                f.truncate()
                try:
                    msg = []
                    for m in self.last_messages:
                        msg.append([mktime(m[0]),m[1],m[2]])
                    json.dump(msg,f)
                finally:
                    f.close();
        except:
            log_exception("Could not write messages to %s: %s"%(get_settings().messages_file, sys.exc_info()[0]))    
    
    def build_info_string(self):
        info_d = {"avatar": get_settings().avatar_file,
                   "name": get_settings().user_name,
                   "next_lunch_begin":get_settings().default_lunch_begin,
                   "next_lunch_end":get_settings().default_lunch_end,
                   "version":get_settings().version_short,
                   "version_commit_count":get_settings().commit_count,
                   "version_commit_count_plugins":get_settings().commit_count_plugins}
        if get_settings().next_lunch_begin:
            info_d["next_lunch_begin"] = get_settings().next_lunch_begin
        if get_settings().next_lunch_end:
            info_d["next_lunch_end"] = get_settings().next_lunch_end
        return json.dumps(info_d)      
        
    def incoming_event(self,data,addr):   
        if addr[0].startswith("127."):
            #stop command is only allowed from localhost :-)
            if data.startswith("HELO_STOP"):
                log_info("Got Stop Command from localhost: %s"%data)
                self.running = False
                self.exitCode = EXIT_CODE_STOP #run_forever script will stop
            elif data.startswith("HELO_UPDATE"):
                self.update_request = True
                if get_settings().auto_update and not self.no_updates:
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
                if get_settings().auto_update and not self.no_updates:
                    log_info("%s: [%s] update"%(t,addr[0]))
                    self.running = False
                    
                    #new update-script:
                    self.exitCode = EXIT_CODE_UPDATE
                else:
                    log_info("%s: %s issued an update but updates are disabled"%( t,addr[0]))
                
            elif cmd.startswith("HELO_REQUEST_DICT"):
                self.member_info[addr[0]] = json.loads(value)
                self.call("HELO_DICT "+json.dumps(self.members),client=addr[0])
                #Request avatar if not there yet
                if self.member_info[addr[0]].has_key("avatar"):
                    if not os.path.exists(get_settings().avatar_dir+"/"+self.member_info[addr[0]]["avatar"]):
                        self.call("HELO_REQUEST_AVATAR "+str(get_settings().tcp_port),client=addr[0])                        
                
            elif cmd.startswith("HELO_DICT"):
                #the master send me the list of members - yeah
                ext_members = json.loads(data.split(" ",1)[1].strip())
                self.members.update(ext_members)
                self.members = dict((k, v) for k, v in self.members.items() if not k.startswith("127"))
                if self.my_master==-1:
                    self.call("HELO_REQUEST_INFO "+self.build_info_string())
                    
                self.my_master = addr[0]                                    
                if not os.path.exists(get_settings().members_file):
                    self.write_members_to_file()
                 
            elif cmd.startswith("HELO_REQUEST_INFO"):
                self.member_info[addr[0]] = json.loads(value)  
                self.call("HELO_INFO "+self.build_info_string(),client=addr[0])
                         
            elif cmd.startswith("HELO_INFO"):
                #someone sends his info
                self.member_info[addr[0]] = json.loads(value)        
                #Request avatar if not there yet
                if self.member_info[addr[0]].has_key("avatar"):
                    if not os.path.exists(get_settings().avatar_dir+"/"+self.member_info[addr[0]]["avatar"]):
                        self.call("HELO_REQUEST_AVATAR "+str(get_settings().tcp_port),client=addr[0])  
                if self.member_info[addr[0]].has_key("name"):         
                    self.members[addr[0]] = self.member_info[addr[0]]["name"]
                                    
            elif cmd.startswith("HELO_LEAVE"):
                #the sender tells me, that he is going
                if addr[0] in self.members:
                    del self.members[addr[0]]                                       
                    self.write_members_to_file()
                self.call("HELO_DICT "+json.dumps(self.members),client=addr[0])
               
            elif cmd.startswith("HELO_AVATAR"):
                #someone want's to send me his pic via TCP
                file_size=int(value.strip())
                file_name=""
                if self.member_info[addr[0]].has_key("avatar"):
                    file_name=get_settings().avatar_dir+os.sep+self.member_info[addr[0]]["avatar"]
                else:
                    log_error("%s tried to send his avatar, but I don't know where to safe it"%(addr[0]))
                
                if len(file_name):
                    log_info("Receiving file of size %d on port %d"%(file_size,get_settings().tcp_port))
                    dr = DataReceiverThread(addr[0],file_size,file_name,get_settings().tcp_port)
                    dr.start()
                
            elif cmd.startswith("HELO_REQUEST_AVATAR"):
                #someone wants my pic 
                other_tcp_port = get_settings().tcp_port
                
                try:                    
                    other_tcp_port=int(value.strip())
                except:
                    log_exception("%s requested avatar, I could not parse the port from value %s, using standard %d"%(str(addr[0]),str(value),other_tcp_port))
                    
                fileToSend = get_settings().avatar_dir+"/"+get_settings().avatar_file
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    log_info("Sending file of size %d to %s : %d"%(fileSize,str(addr[0]),other_tcp_port))
                    self.call("HELO_AVATAR "+str(fileSize), addr[0])
                    ds = DataSenderThread(addr[0],fileToSend, other_tcp_port)
                    ds.start()
                else:
                    log_error("Want to send file %s, but cannot find it"%(fileToSend))   
                
            elif cmd.startswith("HELO_REQUEST_LOGFILE"):
                #someone wants my logfile 
                other_tcp_port = get_settings().tcp_port
                log_num=0
                try:                
                    (oport, onum) = value.split(" ",1)    
                    other_tcp_port=int(oport.strip())
                    log_num = int(onum.strip())
                except:
                    log_exception("%s requested the logfile, I could not parse the port and number from value %s, using standard %d and logfile 0"%(str(addr[0]),str(value),other_tcp_port))
                
                fileToSend = "%s.%d"%(get_settings().log_file,log_num) if log_num>0 else get_settings().log_file
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    log_info("Sending file of size %d to %s : %d"%(fileSize,str(addr[0]),other_tcp_port))
                    self.call("HELO_LOGFILE "+str(fileSize), addr[0])
                    ds = DataSenderThread(addr[0],fileToSend, other_tcp_port)
                    ds.start()
                else:
                    log_error("Want to send file %s, but cannot find it"%(fileToSend))   
            elif "HELO"==cmd:
                #someone tells me his name
                if addr[0] not in self.members:   
                    self.members[addr[0]]=value           
                    self.write_members_to_file()
                    self.call("HELO_INFO "+self.build_info_string(),client=addr[0])
                else:                    
                    self.members[addr[0]]=value
                
                if addr[0] in self.member_info:                    
                    self.member_info[addr[0]]['name']=value
                else:
                    self.member_info[addr[0]]={'name':value}
                    
            else:
                log_info("received unknown command from %s: %s with value %s"%(addr[0],cmd,value))        
                
            member_info = {}
            if self.member_info.has_key(addr[0]):
                member_info = self.member_info[addr[0]]
            for pluginInfo in self.plugin_manager.getPluginsOfCategory("called")+self.plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    try:
                        pluginInfo.plugin_object.process_event(cmd,value,addr[0],member_info)
                    except:
                        log_exception("plugin error in %s while processing event message %s"%(pluginInfo.name, str(sys.exc_info())))
        except:
            log_exception("Unexpected error while handling HELO call: %s"%(str(sys.exc_info())))
            log_critical("The data received was: %s"%data)
        
    
    def incoming_call(self,msg,addr):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        m = addr
        if addr in self.members:
            m = self.members[addr]
            
        log_info("%s: [%s] %s" % (t,m,msg))
        
        self.last_messages.insert(0,[mtime,addr,msg])
        self.new_msg = True
        self.write_messages_to_file()        
        
        if not msg.startswith("ignore"):
            member_info = {}
            if self.member_info.has_key(addr):
                member_info = self.member_info[addr]         
                                
            for pluginInfo in self.plugin_manager.getPluginsOfCategory("called")+self.plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    try:
                        pluginInfo.plugin_object.process_message(msg,addr,member_info)
                    except:
                        log_exception("plugin error in %s while processing message %s"%(pluginInfo.name, str(sys.exc_info())))
                        
            
            if "lunch" in msg.lower() and self.is_now_in_time_span(get_settings().alarm_begin_time, get_settings().alarm_end_time):
                timenum = mktime(mtime)
                if timenum>self.mute_time_until:
                    self.mute_time_until=timenum+get_settings().mute_timeout
                    for pluginInfo in self.plugin_manager.getPluginsOfCategory("called")+self.plugin_manager.getPluginsOfCategory("gui"):
                        if pluginInfo.plugin_object.is_activated:
                            try:
                                pluginInfo.plugin_object.process_lunch_call(msg,addr,member_info)
                            except:
                                log_exception("plugin error in %s while processing lunch call %s"%(pluginInfo.name, str(sys.exc_info())))
                else:
                    log_debug("messages will not trigger alarm: %s: [%s] %s until %s"%(t,m,msg,strftime("%a, %d %b %Y %H:%M:%S", localtime(self.mute_time_until))))
      
                    
    def remove_inactive_members(self):
        try:
            for ip in self.members.keys():
                if ip in self.member_timeout:
                    if time()-self.member_timeout[ip]>get_settings().peer_timeout:
                        del self.members[ip]
                else:
                    del self.members[ip]
        except:
            log_exception("Something went wrong while trying to clean up the members-table")
            
    '''ask for the dictionary and send over own information'''
    def call_for_dict(self):
        try:
            if len(self.members.keys())>self.peer_nr:
                self.call("HELO_REQUEST_DICT "+self.build_info_string(),client=self.members.keys()[self.peer_nr])
            self.peer_nr=(self.peer_nr+1) % len(self.members)
        except:
            log_exception("Something went wrong while trying to send a call to the new master")
            
    '''listening method - should be started in its own thread'''    
    def start_server(self):
        log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Starting the lunch notifier service")
        self.running = True
        self.my_master=-1 #the peer i use as master
        announce_name=0 #how often did I announce my name        
        
        if self.with_plugins:
            try:
                self.plugin_manager.collectPlugins()
            except:
                log_exception("problem when loading plugin: %s"%(str(sys.exc_info())))
            
            #always load these plugins
            self.plugin_manager.activatePluginByName("General Settings", "general") 
            self.plugin_manager.activatePluginByName("Notify", "called") 
        else:
            log_info("lunchinator initialised without plugins")  
            
            
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #getting your IP address is hard...:
        socket.gethostbyname(socket.gethostname()) #may return something like 127.* or 0.*
        if self.own_ip.startswith("127.") or self.own_ip.startswith("0."):
            self.own_ip = socket.gethostbyname(socket.getfqdn())        
        if self.own_ip.startswith("127.") or self.own_ip.startswith("0."):
            log_error("IP address could not be determined, so I'm using your hostname, some things might not work correctly (e.g., statistics)")
            self.own_ip = socket.gethostname()[:15]
            
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            self.init_done.set()
            while self.running:
                if self.new_msg and (time()-mktime(self.last_messages[0][0]))>(get_settings().reset_icon_time*60):
                    self.new_msg=False
                try:
                    daten, addr = s.recvfrom(1024) 
                    if not addr[0].startswith("127."):
                        self.member_timeout[addr[0]]=time()
                        if not self.members.has_key(addr[0]):
                            self.members[addr[0]]=addr[0]
                        
                    if daten.startswith("HELO"):
                        #simple infrastructure protocol messages starting with HELO''' 
                        self.incoming_event(daten, addr)                            
                    else:  
                        #simple message                          
                        self.incoming_call(daten,addr[0])
                except socket.timeout:
                    self.read_config()
                    if self.my_master==-1:
                        self.call_for_dict()
                    else:
                        if announce_name==10:
                            #it's time to announce my name again and switch the master
                            self.call("HELO "+get_settings().get_user_name(),hosts=self.members)
                            announce_name=0
                            self.remove_inactive_members()
                            self.call_for_dict()
                        else:
                            #just wait for the next time when i have to announce my name
                            announce_name+=1
                    if self.my_master==-1:
                        log_info("no master found yet")
                    log_debug(str(self.members.keys()))
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
            log_info("Lunchinator stopped")                  
            log_info(strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service")
#            self.write_config_to_hd()
            for pluginInfo in self.plugin_manager.getAllPlugins():
                if pluginInfo.plugin_object.is_activated:
                    pluginInfo.plugin_object.deactivate()
            os._exit(self.exitCode)
            
    def get_last_msgs(self):  
        return self.last_messages
    
    def get_members(self):  
        return self.members

    def get_member_timeout(self):  
        return self.member_timeout    
    
    def get_member_info(self):  
        return self.member_info    
