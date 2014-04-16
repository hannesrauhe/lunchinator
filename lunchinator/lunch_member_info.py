from time import time

class LunchMemberInfo(object):
    def __init__(self):
        self._all_members = set()
        self._member_timeout = {}  # TODO was _peer_timeout
        self._member_info = {}  # TODO was peer_info
        self._groups = set()  # TODO was peer_groups
    
    def get_groups(self):  
        return self._peer_groups
    
    def get_all_members(self):  # TODO was get_members
        return self._all_members
    
    def get_all_members_count(self):
        return len(self._all_members)
    
    def get_group_members(self):
        return [ip for ip in self.get_all_members() if self.is_member_in_my_group(ip)]
    
    def get_member_timeout(self):  
        return self._peer_timeout    
    
    def get_peer_timeout(self):  
        return self._peer_timeout

    def __len__(self):
        return len(self._all_members)

    def __iter__(self):
        return self._all_members.__iter__()
    
    def __contains__(self, ip):
        return ip in self._all_members
    
    def knowsMember(self, ip):
        return ip in self
    
    def getTimedOutMembers(self, timeout):
        result = set()
        for ip in self:
            if ip in self._member_timeout:
                if time() - self._member_timeout[ip] > timeout:
                    result.add(ip)
            else:
                result.add(ip)

        return result
    
    def removeMembers(self, toRemove):
        if type(toRemove) != set:
            toRemove = set(toRemove)
        
        self._all_members -= toRemove
                