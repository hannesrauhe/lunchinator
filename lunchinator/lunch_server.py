#!/usr/bin/python
from lunch_datathread import *
from lunch_default_config import *
from iface_plugins import *
from time import strftime, localtime, time, mktime, gmtime
import socket,subprocess,sys,os,ctypes,getpass,json

from yapsy.PluginManager import PluginManagerSingleton
from yapsy.ConfigurablePluginManager import ConfigurablePluginManager

EXIT_CODE_UPDATE = 2
EXIT_CODE_STOP = 3
        
class lunch_server(lunch_default_config):    
    running = False
    update_request = False
    new_msg = False
    my_master = -1    
    peer_nr=0 #the number of the peer i contacted to be my master
    mute_time_until=0
    last_messages = []
    members = {}
    member_timeout = {}
    member_info = {}
    plugin_manager = None
    no_updates = False
    with_plugins = True
    
    #TODO: if started with plugins: make sure they are deactivated when destroying lunchinator (destructor anyone?)
    def __init__(self, noUpdates = False, withPlugins = True):            
        lunch_default_config.__init__(self)
        self.no_updates = noUpdates
        self.with_plugins = withPlugins      
        self.exitCode = 0  
        self.read_config()
        
        PluginManagerSingleton.setBehaviour([
            ConfigurablePluginManager,
        ])
        self.plugin_manager = PluginManagerSingleton.get()
        self.plugin_manager.app = self
        self.plugin_manager.setConfigParser(self.config_file,self.write_config_to_hd)
        self.plugin_manager.setPluginPlaces(self.plugin_dirs)
        self.plugin_manager.setCategoriesFilter({
           "general" : iface_general_plugin,
           "called" : iface_called_plugin,
           "gui" : iface_gui_plugin
           }) 
        self.init_done = threading.Event()
        self.shared_dict = {} #for plugins
        
    def is_now_in_time_span(self,begin,end):
        try:
            begin_hour,_,begin_min = begin.partition(":")
            end_hour,_,end_min = end.partition(":")
            return localtime()[3]*60+localtime()[4] >= int(begin_hour)*60+int(begin_min) and localtime()[3]*60+localtime()[4] <= int(end_hour)*60+int(end_min)
        except:
            self.lunch_logger.error("don't know how to handle time span %s"%(str(sys.exc_info())))
            return False;
        
    def call(self,msg,client='',hosts={}):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        i=0
        #print "sending",msg,"to",
        if client:
            self.lunch_logger.debug("Sending message %s to %s"%(msg,client))
            #print client
            try:
                s.sendto(msg, (client.strip(), 50000)) 
                i+=1
            except:
                self.lunch_logger.error("Exception while sending msg %s to %s: %s"%(msg,client, str(sys.exc_info()[0])))
        elif 0==len(hosts):
            members = self.members
            if 0==len(members):
                members = self.init_members_from_file()            
            if 0==len(members):
                self.lunch_logger("Cannot send message, no peers connected, no peer found in members file")
                return 0
            self.lunch_logger.debug("Sending message %s to %s"%(msg,str(members)))
            for ip,name in members.items():
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    i+=1
                except:
                    self.lunch_logger.error("Exception while sending msg %s to %s: %s"%(msg,client, str(sys.exc_info()[0])))
                    continue        
        else:
            self.lunch_logger.debug("Sending message %s to %s",msg,str(hosts))
            for ip,name in hosts.items():
                #print ip.strip()
                try:
                    s.sendto(msg, (ip.strip(), 50000))
                    i+=1
                except:
                    self.lunch_logger.error("Exception while sending msg %s to %s: %s"%(msg,client, str(sys.exc_info()[0])))
                    continue
        
        s.close() 
        return i
        
    '''short for the call function above for backward compatibility'''
    def call_all_members(self,msg):        
        self.call(msg,hosts=self.members)   
        
        
    '''will be called every ten seconds'''
    def read_config(self):                    
        self.read_config_from_hd()
        if len(self.members)==0:
            self.members=self.init_members_from_file()
        if len(self.last_messages)==0:
            self.last_messages=self.init_messages_from_file()
            
            
    def init_members_from_file(self):
        members = {}
        if os.path.exists(self.members_file):
            f = open(self.members_file,'r')    
            for hostn in f.readlines():
                try:
                    members[socket.gethostbyname(hostn.strip())]=hostn.strip()
                except:
                    self.lunch_logger.warn("cannot find host specified in members_file by %s with name %s"%(self.members_file,hostn))
            f.close()
        return members
    
    def write_members_to_file(self):
        try:
            if len(self.members)>1:
                f = open(self.members_file,'w')
                f.truncate()
                for m in self.members.keys():
                    f.write(m+"\n")
                f.close();
        except:
            self.lunch_logger.error("Could not write members to %s"%(self.members_file))
            
    def init_messages_from_file(self):
        messages = []
        if os.path.exists(self.messages_file):
            try:
                f = open(self.messages_file,'r')    
                tmp_msg = json.load(f)
                for m in tmp_msg:
                    messages.append([localtime(m[0]),m[1],m[2]])
                f.close()
            except:
                self.lunch_logger.error("Could not read messages file %s,but it seems to exist"%(self.messages_file))
        return messages
    
    def write_messages_to_file(self):
        try:
            if len(self.last_messages)>0:
                f = open(self.messages_file,'w')
                f.truncate()
                try:
                    msg = []
                    for m in self.last_messages:
                        msg.append([mktime(m[0]),m[1],m[2]])
                    json.dump(msg,f)
                finally:
                    f.close();
        except:
            self.lunch_logger.error("Could not write messages to %s: %s"%(self.messages_file, sys.exc_info()[0]))    
    
    def build_info_string(self):
        info_d = {"avatar": self.avatar_file,
                   "name": self.user_name,
                   "next_lunch_begin":self.default_lunch_begin,
                   "next_lunch_end":self.default_lunch_end,
                   "version":self.version_short,
                   "version_commit_count":self.commit_count,
                   "version_commit_count_plugins":self.commit_count_plugins}
        if self.next_lunch_begin:
            info_d["next_lunch_begin"] = self.next_lunch_begin
        if self.next_lunch_end:
            info_d["next_lunch_end"] = self.next_lunch_end
        return json.dumps(info_d)
    
    def send_info_around(self):
        self.call("HELO_INFO "+self.build_info_string())          
        
    def incoming_event(self,data,addr):   
        if addr[0].startswith("127."):
            #stop command is only allowed from localhost :-)
            if data.startswith("HELO_STOP"):
                self.lunch_logger.info("Got Stop Command from localhost: %s"%data)
                self.running = False
                self.exitCode = EXIT_CODE_STOP #run_forever script will stop
            elif data.startswith("HELO_UPDATE"):
                self.update_request = True
                if self.auto_update and not self.no_updates:
                    self.lunch_logger.info("local update")
                    self.running = False
                    
                    #new update-script:
                    self.exitCode = EXIT_CODE_UPDATE
                else:
                    self.lunch_logger.info("local update issued but updates are disabled")
            #only stop and update command is allowed from localhost, returning here
            return     
                
        try:        
            (cmd, value) = data.split(" ",1)
            if cmd.startswith("HELO_UPDATE"):
                t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                self.update_request = True
                if self.auto_update and not self.no_updates:
                    self.lunch_logger.info("%s: [%s] update"%(t,addr[0]))
                    self.running = False
                    
                    #new update-script:
                    self.exitCode = EXIT_CODE_UPDATE
                else:
                    self.lunch_logger.info("%s: %s issued an update but updates are disabled"%( t,addr[0]))
                
            elif cmd.startswith("HELO_REQUEST_DICT"):
                self.member_info[addr[0]] = json.loads(value)
                self.call("HELO_DICT "+json.dumps(self.members),client=addr[0])
                #Request avatar if not there yet
                if self.member_info[addr[0]].has_key("avatar"):
                    if not os.path.exists(self.avatar_dir+"/"+self.member_info[addr[0]]["avatar"]):
                        self.call("HELO_REQUEST_AVATAR "+str(self.tcp_port),client=addr[0])                        
                
            elif cmd.startswith("HELO_DICT"):
                #the master send me the list of members - yeah
                ext_members = json.loads(data.split(" ",1)[1].strip())
                self.members.update(ext_members)
                self.members = dict((k, v) for k, v in self.members.items() if not k.startswith("127"))
                if self.my_master==-1:
                    self.send_info_around()
                    
                self.my_master = addr[0]                                    
                if not os.path.exists(self.members_file):
                    self.write_members_to_file()
                                    
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
                    file_name=self.avatar_dir+"/"+self.member_info[addr[0]]["avatar"]
                else:
                    self.lunch_logger.error("%s tried to send his avatar, but I don't know where to safe it"%(addr[0]))
                
                if len(file_name):
                    self.lunch_logger.info("Receiving file of size %d on port %d"%(file_size,self.tcp_port))
                    dr = DataReceiverThread(addr[0],file_size,file_name,self.tcp_port)
                    dr.start()
                
            elif cmd.startswith("HELO_REQUEST_AVATAR"):
                #someone wants my pic 
                other_tcp_port = self.tcp_port
                
                try:                    
                    other_tcp_port=int(value.strip())
                except:
                    self.lunch_logger.error("%s requested avatar, I could not parse the port from value %s, using standard %d"%(str(addr[0]),str(value),other_tcp_port))
                    
                fileToSend = self.avatar_dir+"/"+self.avatar_file
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    self.lunch_logger.info("Sending file of size %d to %s : %d"%(fileSize,str(addr[0]),other_tcp_port))
                    self.call("HELO_AVATAR "+str(fileSize), addr[0])
                    ds = DataSenderThread(addr[0],fileToSend, other_tcp_port)
                    ds.start()
                else:
                    self.lunch_logger.error("Want to send file %s, but cannot find it"%(fileToSend))   
               
            elif cmd.startswith("HELO_LOGFILE"):
                #someone will send me his logfile on tcp
                file_size=int(value.strip())
                if not os.path.exists(self.main_config_dir+"/logs"):
                    os.makedirs(self.main_config_dir+"/logs")
                file_name=self.main_config_dir+"/logs/"+str(addr[0])+".log"
                self.lunch_logger.info("Receiving file of size %d on port %d"%(file_size,self.tcp_port))
                dr = DataReceiverThread(addr[0],file_size,file_name,self.tcp_port)
                dr.start()
                
            elif cmd.startswith("HELO_REQUEST_LOGFILE"):
                #someone wants my logfile 
                other_tcp_port = self.tcp_port
                log_num=""
                try:                
                    (oport, log_num) = value.split(" ",1)    
                    other_tcp_port=int(oport.strip())
                except:
                    self.lunch_logger.error("%s requested the logfile, I could not parse the port and number from value %s, using standard %d and logfile 0"%(str(addr[0]),str(value),other_tcp_port))
                
                fileToSend = "%s.%s"%(self.log_file,log_num) if len(log_num.strip()) else self.log_file
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    self.lunch_logger.info("Sending file of size %d to %s : %d"%(fileSize,str(addr[0]),other_tcp_port))
                    self.call("HELO_LOGFILE "+str(fileSize), addr[0])
                    ds = DataSenderThread(addr[0],fileToSend, other_tcp_port)
                    ds.start()
                else:
                    self.lunch_logger.error("Want to send file %s, but cannot find it"%(fileToSend))   
                      
            elif cmd.startswith("HELO_INFO"):
                #someone sends his info
                self.member_info[addr[0]] = json.loads(value)      
                #Request avatar if not there yet
                if self.member_info[addr[0]].has_key("avatar"):
                    if not os.path.exists(self.avatar_dir+"/"+self.member_info[addr[0]]["avatar"]):
                        self.call("HELO_REQUEST_AVATAR "+str(self.tcp_port),client=addr[0])          
                
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
                self.lunch_logger.info("received unknown command from %s: %s with value %s"%(addr[0],cmd,value))        
                
            member_info = {}
            if self.member_info.has_key(addr[0]):
                member_info = self.member_info[addr[0]]
            for pluginInfo in self.plugin_manager.getPluginsOfCategory("called")+self.plugin_manager.getPluginsOfCategory("gui"):
                if pluginInfo.plugin_object.is_activated:
                    try:
                        pluginInfo.plugin_object.process_event(cmd,value,addr[0],member_info)
                    except:
                        self.lunch_logger.exception("plugin error in %s while processing event message %s"%(pluginInfo.name, str(sys.exc_info())))
        except:
            self.lunch_logger.critical("Unexpected error while handling HELO call: %s"%(str(sys.exc_info())))
            self.lunch_logger.critical("The data received was: %s"%data)
        
    
    def incoming_call(self,msg,addr):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        m = addr
        if addr in self.members:
            m = self.members[addr]
            
        print "%s: [%s] %s" % (t,m,msg)
        
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
                        self.lunch_logger.exception("plugin error in %s while processing message %s"%(pluginInfo.name, str(sys.exc_info())))
                        
            
            if "lunch" in msg.lower() and self.is_now_in_time_span(self.alarm_begin_time, self.alarm_end_time):
                timenum = mktime(mtime)
                if timenum>self.mute_time_until:
                    self.mute_time_until=timenum+self.mute_timeout
                    for pluginInfo in self.plugin_manager.getPluginsOfCategory("called")+self.plugin_manager.getPluginsOfCategory("gui"):
                        if pluginInfo.plugin_object.is_activated:
                            try:
                                pluginInfo.plugin_object.process_lunch_call(msg,addr,member_info)
                            except:
                                self.lunch_logger.exception("plugin error in %s while processing lunch call %s"%(pluginInfo.name, str(sys.exc_info())))
                else:
                    self.lunch_logger.debug("messages will not trigger alarm: %s: [%s] %s until %s"%(t,m,msg,strftime("%a, %d %b %Y %H:%M:%S", localtime(self.mute_time_until))))
      
                    
    def remove_inactive_members(self):
        try:
            for ip in self.members.keys():
                if ip in self.member_timeout:
                    if time()-self.member_timeout[ip]>self.peer_timeout:
                        del self.members[ip]
                else:
                    del self.members[ip]
        except:
            self.lunch_logger.error("Something went wrong while trying to clean up the members-table")
            
    '''ask for the dictionary and send over own information'''
    def call_for_dict(self):
        try:
            if len(self.members.keys())>self.peer_nr:
                self.call("HELO_REQUEST_DICT "+self.build_info_string(),client=self.members.keys()[self.peer_nr])
            self.peer_nr=(self.peer_nr+1) % len(self.members)
        except:
            self.lunch_logger.error("Something went wrong while trying to send a call to the new master")
            
    '''listening method - should be started in its own thread'''    
    def start_server(self):
        print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Starting the lunch notifier service"
        self.running = True
        self.my_master=-1 #the peer i use as master
        announce_name=0 #how often did I announce my name        
        
        if self.with_plugins:
            try:
                self.plugin_manager.collectPlugins()
            except:
                self.lunch_logger.exception("problem when loading plugin: %s"%(str(sys.exc_info())))
            
            #always load these plugins
            self.plugin_manager.activatePluginByName("General Settings", "general") 
            self.plugin_manager.activatePluginByName("Notify", "called") 
        else:
            self.lunch_logger.info("lunchinator initialised without plugins")  
            
            
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            self.init_done.set()
            while self.running:
                if self.new_msg and (time()-mktime(self.last_messages[0][0]))>(self.reset_icon_time*60):
                    self.new_msg=False
                try:
                    daten, addr = s.recvfrom(1024) 
                    
                    if not addr[0].startswith("127."):
                        self.member_timeout[addr[0]]=time()
                        
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
                            self.call("HELO "+self.get_user_name(),hosts=self.members)
                            announce_name=0
                            self.remove_inactive_members()
                            self.call_for_dict()
                        else:
                            #just wait for the next time when i have to announce my name
                            announce_name+=1
                    if self.my_master==-1:
                        self.lunch_logger.info("no master found yet")
                    self.lunch_logger.debug(str(self.members.keys()))
        except socket.error as e:
            self.lunch_logger.critical("stopping lunchinator because: %s"%(str(e)))
        except:
            self.lunch_logger.critical("stopping - Critical error: %s"%str(sys.exc_info())) 
        finally: 
            try:
                self.call("HELO_LEAVE bye")
                s.close()  
            except:
                self.lunch_logger.warning("Wasn't able to send the leave call and close the socket...")
            self.lunch_logger.info("Lunchinator stopped")                  
            print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service"
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
