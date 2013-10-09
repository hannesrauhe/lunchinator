import shlex, inspect
from lunchinator import get_server, log_exception

class LunchCLIModule(object):
    def getHostList(self, args):
        hosts = []
        for member in args:
            if len(member) == 0:
                continue
            ip = get_server().ipForMemberName(member)
            if ip != None:
                hosts.append(ip)
            else:
                # assume IP or host name
                hosts.append(member)
        return hosts
    
    def completeHostnames(self, text):
        get_server().lockMembers()
        lunchmembers = None
        try:
            lunchmemberNames = set([get_server().memberName(ip) for ip in get_server().get_members() if get_server().memberName(ip).startswith(text)])
            lunchMemberIPs = set([ip for ip in get_server().get_members() if ip.startswith(text)])
            lunchmembers = list(lunchmemberNames.union(lunchMemberIPs))
        finally:
            get_server().releaseMembers()
        return lunchmembers if lunchmembers != None else []
    
    def getArgNum(self, text, line, _begidx, endidx):
        prevArgs = shlex.split(line[:endidx + 1])
        argNum = len(prevArgs)
        
        if len(text) > 0 or prevArgs[-1][-1] == ' ':
            # the current word is the completed word
            return (argNum - 1, prevArgs[-1].replace(" ", "\\ "))
        # complete an empty word
        return (argNum, "")