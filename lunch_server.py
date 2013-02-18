#!/usr/bin/python
from lunch_datathread import *
from lunch_client import *
from lunch_default_config import *

from time import strftime, localtime, time, mktime
import socket,subprocess,sys,os,ctypes,getpass,json
        
class lunch_server(lunch_default_config):    
    running = False
    update_request = False
    new_msg = False
    my_master = -1    
    peer_nr=0 #the number of the peer i contacted to be my master
    last_messages = []
    members = {}
    member_timeout = {}
    member_info = {}
    lclient = lunch_client()
    
    '''will be called every ten seconds'''
    def read_config(self):             
        self.debug = False
        for config_path in self.config_dirs:                
            if os.path.exists(config_path+"/debug.cfg"):
                self.debug = True
                
            if os.path.exists(config_path+"/username.cfg"):
                with open(config_path+"/username.cfg") as f:
                    self.user_name = f.readline().strip()
                    
            if os.path.exists(config_path+"/avatar.cfg"):
                with open(config_path+"/avatar.cfg") as f:
                    self.avatar_file = f.readline().strip()
                    
            if os.path.exists(config_path+"/sound.cfg"):
                with open(config_path+"/sound.cfg") as f:
                    audio_file = f.readline().strip()
                    if os.path.exists(config_path+"/sounds/"+audio_file):
                        self.audio_file = audio_file
                    else:
                        print "configured audio file "+audio_file+" does not exist in sounds folder, using old one: "+self.audio_file                        
                        
        if len(self.members)==0:
            self.members=self.init_members_from_file()
        
        if self.user_name=="":
            self.user_name = getpass.getuser()
        
    def get_user_name(self):
        return self.user_name
    
    def incoming_event(self,data,addr):   
        if addr[0].startswith("127."):
            return     
        
        (cmd, value) = data.split(" ",1)
                
        try:
            if cmd.startswith("HELO_UPDATE"):
                t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
                if self.auto_update:
                    print "%s: [%s] update" % (t,addr)
                    os.chdir(sys.path[0])
                    subprocess.call(["git","stash"])
                    subprocess.call(["git","pull"])
                else:
                    print "%s: %s issued an update but updates are disabled" % (t,addr)
                self.update_request = True
                
            elif cmd.startswith("HELO_REQUEST_DICT"):
                self.member_info[addr[0]] = json.loads(value)
                self.lclient.call("HELO_DICT "+json.dumps(self.members),client=addr[0])
                #Request avatar if not there yet
                if self.member_info[addr[0]].has_key("avatar"):
                    if not os.path.exists(self.avatar_dir+"/"+self.member_info[addr[0]]["avatar"]):
                        self.lclient.call("HELO_REQUEST_AVATAR ",client=addr[0])
                self.write_info_html()
                        
                
            elif cmd.startswith("HELO_DICT"):
                #the master send me the list of members - yeah
                ext_members = json.loads(data.split(" ",1)[1].strip())
                self.members.update(ext_members)
                self.members = dict((k, v) for k, v in self.members.items() if not k.startswith("127"))
                if self.my_master==-1:                    
                    self.lclient.call("HELO "+self.get_user_name(),hosts=self.members)
                    
                self.my_master = addr[0]                                    
                if not os.path.exists(self.members_file):
                    self.write_members_to_file()
               
            elif cmd.startswith("HELO_AVATAR"):
                #someone want's to send me his pic via TCP
                file_size=int(value.strip())
                if self.debug:
                    print "Receiving file of size",file_size
                if self.member_info[addr[0]].has_key("avatar"):
                    dr = DataReceiverThread(addr[0],file_size,self.avatar_dir+"/"+self.member_info[addr[0]]["avatar"])
                    dr.start()
                else:
                    print addr[0],"tried to send his avatar, but I don't know where to safe it"
                
            elif cmd.startswith("HELO_REQUEST_AVATAR"):
                #someone wants my pic 
                fileToSend = self.avatar_dir+"/"+self.avatar_file
                if os.path.exists(fileToSend):
                    fileSize = os.path.getsize(fileToSend)
                    self.lclient.call("HELO_AVATAR "+str(fileSize), addr[0])
                    ds = DataSenderThread(addr[0],fileToSend)
                    ds.start()
                else:
                    print "File",fileToSend,"not found"                    
                                    
            elif cmd.startswith("HELO_MASTER"):
                #deprecated
                if addr[0] in self.members:
                    self.members[addr[0]]=value
                else:
                    self.members[addr[0]]={'name':value}                                        
                    self.write_members_to_file()
                self.lclient.call("HELO_DICT "+json.dumps(self.members),client=addr[0])
                
            elif "HELO"==cmd:
                #someone tells me his name
                if addr[0] in self.members:
                    self.members[addr[0]]=value
                else:
                    self.members[addr[0]]={'name':value}                                        
                    self.write_members_to_file()
                
                if addr[0] in self.member_info:                    
                    self.member_info[addr[0]]['name']=value
                else:
                    self.member_info[addr[0]]={'name':value}
                    
            else:
                print "unknown command",cmd,"with value",value
        except:
            print "Unexpected error while handling HELO call: ", sys.exc_info()[0]
            print "The data send was:",data
        
    
    def incoming_call(self,msg,addr):
        mtime = localtime()
        
        t = strftime("%a, %d %b %Y %H:%M:%S", localtime())
        m = addr
        if addr in self.members:
            m = self.members[addr]
            
        if len(self.last_messages)>0:
            last = self.last_messages[0]            
            if msg==last[2] and mktime(mtime)-mktime(last[0])<self.mute_timeout:
                if self.debug:
                    print "a second message with the same text arrived within",self.mute_timeout, "seconds: "
                    print "%s: [%s] %s" % (t,m,msg)
                return
            if addr==last[1] and mktime(mtime)-mktime(last[0])<self.mute_timeout:
                if self.debug:
                    print "somebody sent two msgs in a row - was muted: "
                    print "%s: [%s] %s" % (t,m,msg)
                return
            
        print "%s: [%s] %s" % (t,m,msg)
        
        self.last_messages.insert(0,(mtime,addr,msg))
        self.new_msg = True
        
        if not msg.startswith("ignore"):
            if sys.platform.startswith('linux'):
                self.incoming_call_linux(msg,addr)
            else:
                self.incoming_call_win(msg,addr)
            
    def incoming_call_linux(self,msg,addr):    
        try:
            icon = self.icon_file
            if self.member_info.has_key(addr) and self.member_info[addr].has_key("avatar"):
                icon = self.avatar_dir+"/"+self.member_info[addr]["avatar"]
            subprocess.call(["notify-send","--icon="+icon, msg + " [" + self.members[addr] + "]"])
        except:
            print "notify error"
            pass
    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765:
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                print "eject error (open)"
                pass
        
            try:
                subprocess.call(["play", "-q", sys.path[0]+"/sounds/"+self.audio_file])    
            except:
                print "sound error"
                pass
        
            try:
                subprocess.call(["eject", "-T", "/dev/cdrom"])
            except:
                print "eject error (close)"
                pass
        
    def incoming_call_win(self,msg,addr):    
        if localtime()[3]*60+localtime()[4] >= 705 and localtime()[3]*60+localtime()[4] <= 765:
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                print "eject error (open)"
                pass
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                print "eject error (close)"
                pass
            
    def init_members_from_file(self):
        members = {}
        if os.path.exists(self.members_file):
            f = open(self.members_file,'r')    
            for hostn in f.readlines():
                try:
                    members[socket.gethostbyname(hostn.strip())]=hostn.strip()
                except:
                    print "cannot find host specified by",self.members_file,"with name",hostn
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
            print "Could not write",self.members_file

    
    def remove_inactive_members(self):
        try:
            for ip in self.members.keys():
                if ip in self.member_timeout:
                    if time()-self.member_timeout[ip]>self.peer_timeout:
                        del self.members[ip]
                else:
                    del self.members[ip]
        except:
            print "Something went wrong while trying to clean up the members-table"
            
    '''ask for the dictionary and send over own information'''
    def call_for_dict(self):
        try:
            if len(self.members.keys())>self.peer_nr:
                self.lclient.call("HELO_REQUEST_DICT "+json.dumps({"avatar": self.avatar_file,
                                                             "name": self.user_name}),
                                                             client=self.members.keys()[self.peer_nr])
            self.peer_nr=(self.peer_nr+1) % len(self.members)
        except:
            print "Something went wrong while trying to send a call to the new master"
            
        
    def start_server(self):
        print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Starting the lunch notifier service"
        self.running = True
        self.my_master=-1 #the peer i use as master
        self.user_name=getpass.getuser()
        announce_name=0 #how often did I announce my name
        
        self.read_config()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            while self.running:
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
                            self.lclient.call("HELO "+self.get_user_name(),hosts=self.members)
                            announce_name=0
                            self.remove_inactive_members()
                            self.call_for_dict()
                        else:
                            #just wait for the next time when i have to announce my name
                            announce_name+=1
                    if self.debug:
                        if self.my_master==-1:
                            print "no master found yet"
                        print self.members.keys()
        finally: 
            s.close()                    
            print strftime("%a, %d %b %Y %H:%M:%S", localtime()),"Stopping the lunch notifier service"
            
    def write_info_html(self):
        indexhtml = open(self.html_dir+"/index.html","w")
        indexhtml.write("<title>Lunchinator</title><meta http-equiv='refresh' content='5' ><table>")
        if len(self.member_info)>0:
            for ip,d in self.member_info.iteritems():
                indexhtml.write("<tr><td>"+str(ip)+"</td>")
                if d.has_key("avatar"):
                    indexhtml.write("<td><img width='200' src=\"avatars/"+d["avatar"]+"\" /></td>")
                indexhtml.write("</tr>")
        indexhtml.write("</table>")
        indexhtml.close()
    
if __name__ == "__main__":
    l = lunch_server()
    l.start_server()
