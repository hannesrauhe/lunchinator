#!/usr/bin/python
# coding=utf-8

import socket, sys, json
from time import time

def log_error(msg):
    print "ERROR:", msg

def log_info(msg):
    print "INFO:", msg
    
def log_debug(msg):
    print "DEBUG:", msg
        
class lunch_server(object):        
    def __init__(self):
        super(lunch_server, self).__init__()
        self.running = False
        self._peer_nr = 0  # the number of the peer i contacted to be my master
        
        # here we store every info we can get        
        self._peer_info = {}
        
        # a member is a peer in our group that who told me about him/herself in the last x sec
        self._members = set()
        
        # we store the time of the direct contact
        self._peer_timeout = {}
        
        # these are the peers we did not get infos from yet
        self._new_peers = set()  
        
        self.exitCode = 0  
        
        self.info = { u"name": u"Lunchinator Test Instance",
                   u"group": u""}
        self.own_group = ""
    
    def _build_info_string(self):        
        return json.dumps(self.info)

    '''listening method - should be started in its own thread'''    
    def start_server(self):
        self.running = True
        self.my_master = -1  # the peer i use as master
        announce_name = -1  # how often did I announce my name
        cmd = ""
        value = ""
                
        is_in_broadcast_mode = False
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: 
            s.bind(("", 50000)) 
            s.settimeout(5.0)
            while self.running:
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
                        continue
                    
                    log_debug("%s: %s" % (ip, data))
                    
                    # first we save the timestamp of this contact, no matter what
                    self._peer_timeout[ip] = time()
                    
                    # we also make sure, that there is a valid record for this ip,
                    # so we do not have to check this every time
                    self._create_valid_peer(ip)
                    
                    # if there is no HELO in the beginning, it's just a message and 
                    # we handle it, if the peer is in our group
                    if not data.startswith("HELO"):
                        if not ip in self._members:
                            print "New message:", data
                        else:
                            log_info("Dropped a message from %s: %s" % (ip, data))
                        continue
                                                
                    try:
                        # commands must always have additional info:
                        (cmd, value) = data.split(" ", 1)
                    except:
                        log_error("Command of %s has no payload: %s" % (ip, data))
                    
                    # if this packet has info about the peer, we record it and
                    # are done
                    if self._record_info(ip, cmd, value):
                        continue
                    
                    # the rest is only interesting if the peer is in our group
                    if not ip in self._members:
                        continue
                            
                    self._handle_incoming_event(ip, cmd, value) 
                        
                except socket.timeout:
                    if len(self._members) > 1:                        
                        if is_in_broadcast_mode:
                            is_in_broadcast_mode = False
                            log_info("ending broadcast")
                        
                        if len(self._new_peers):
                            self.call_request_info(self._new_peers)
                            self._new_peers.clear()
                            
                        if announce_name == -1:
                            # thats how we start
                            self.call_request_info()
                        if announce_name == 10:
                            # a simple ping to everyone
                            self.call("HELO " + self.info["name"])
                            announce_name = 0
                            self._remove_inactive_members()
                            self.call_request_dict()
                        else:
                            announce_name += 1
                    else:
                        if not is_in_broadcast_mode:
                            is_in_broadcast_mode = True
                            log_info("broadcasting")
                        self._broadcast()
        finally:
            self.call("HELO_LEAVE bye")
            s.close()  
                
    def _create_valid_peer(self, ip, info={}):        
        if ip not in self._peer_info:
            log_info("new peer: %s" % ip)
            self._peer_info[ip] = dict({u"name":ip, u"group":u""}.items() + info.items())
            self._new_peers.add(ip)      
            
    def _record_info(self, ip, cmd, value):
        if cmd == "HELO_INFO":
            self._update_peer_info(ip, json.loads(value))
            return True
        elif cmd == "HELO_REQUEST_INFO":
            self._update_peer_info(ip, json.loads(value))
            self.call_info()
            return True
            
    def _update_peer_info(self, ip, info_dict):
        if ip in self._new_peers:
            self._new_peers.remove(ip)
        self._peer_info[ip].update(info_dict)
        
        if ip not in self._members and 0 == len(self.own_group):
            self._add_member(ip)
        elif ip not in self._members and self._peer_info[ip][u"group"] == self.own_group:
            self._add_member(ip)
        elif ip in self._members and self._peer_info[ip][u"group"] != self.own_group:
            self._remove_member(ip)
            
    def _handle_incoming_event(self, ip, cmd, value):                  
        if cmd == "HELO_REQUEST_DICT":
            self._update_peer_info(ip, json.loads(value))                   
            
        elif cmd == "HELO_DICT":
            # the master send me the list of _members - yeah
            ext_members = json.loads(value)
            # i add every entry and assume, the member is in my group
            # i will still ask the member itself 
            for m_ip, m_name in ext_members.iteritems():
                self._create_valid_peer(m_ip, {u"name":m_name, u"group":self.own_group})
                                
        elif cmd == "HELO_LEAVE":
            self._remove_member(ip)
            
        elif cmd == "HELO":
            # this is just a ping with the members name
            self._update_peer_info(ip, {u"name":""})
            
        else:
            self.log_msg("received unknown command from %s: %s with value %s" % (ip, cmd, value))
                    
    def _remove_inactive_members(self):
        ip2remove = []
        for ip in self._members:
            if time() - self._peer_timeout[ip] > 300:
                ip2remove.append(ip)
        
        for ip in ip2remove:
            self._remove_member(ip)
            
    def _add_member(self, ip):
        self._members.add(ip)
        log_info("%s has joined our group" % ip)
        
    def _remove_member(self, ip):
        self._members.pop(ip)
        log_info("%s has left our group" % ip)
    
    def _broadcast(self):
        try:
            s_broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s_broad.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s_broad.sendto('HELO_REQUEST_INFO ' + self._build_info_string(), ('255.255.255.255', 50000))
            s_broad.close()
        except:
            log_error("Problem while broadcasting")
            
            
            
    ''' public functions '''
            
            
            
    '''An info call informs a peer about my name etc...
    by default to every peer'''
    def call_info(self, peers=[]):
        if 0 == len(peers):
            peers = self._peer_info.keys()
        return self.call("HELO_INFO " + self._build_info_string(), peers)  
    
    '''Similar to a info call but also request information from the peer
    by default to every/from every peer'''
    def call_request_info(self, peers=[]):
        if 0 == len(peers):
            peers = self._peer_info.keys()
        return self.call("HELO_INFO " + self._build_info_string(), peers)
    
    '''One member at a time will get my list of peers'''
    def call_dict(self, ip):        
        members_dict = {}
        for ip in self._members:
            members_dict[ip] = self._peer_info[ip][u'name']
        self.call("HELO_DICT " + json.dumps(members_dict), [ip]) 
        
    '''round robin we ask every member for his peers, but one by one.
    Sometimes the member asked is referred to as master'''
    def call_request_dict(self):
        if len(self._members) > self._peer_nr:
            self.call("HELO_REQUEST_DICT " + self._build_info_string(), [list(self._members)[self._peer_nr]])
        if len(self._members) > 0:
            self._peer_nr = (self._peer_nr + 1) % len(self._members)
    
    '''send a message - by default to every member'''
    def call(self, msg, peers=[]):
        if 0 == len(peers):
            peers = self._members
        if 0 == len(peers):
            log_error("Cannot send a message %s, there is no peer to send to" % msg)
            return 0

        i = 0
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        try:      
            for ip in peers:
                try:
                    s.sendto(msg.encode('utf-8'), (ip.strip(), 50000))
                    i += 1
                except:
                    log_error("Message %s could not be delivered to %s: %s" % (s, ip, str(sys.exc_info()[0])))
                    continue
        finally:
            s.close()
             
        return i            
    
    def changeGroup(self, newgroup):
        self.info["group"] = unicode(newgroup)
        self.call("HELO_LEAVE Changing Group")
        self.call("HELO_REQUEST_INFO " + json.dumps(self.info))
        
if __name__ == "__main__":
    s = lunch_server()
    s.start_server()
            

