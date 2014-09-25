from lunchinator.plugin import iface_gui_plugin
from lunchinator import get_server, get_settings, get_peers, convert_string
from lunchinator.utilities import displayNotification
import json

class voter(iface_gui_plugin):
    def __init__(self):
        super(voter, self).__init__()
        self.w = None
        
        self.vote_count = {}
        self.ip2vote = {}        
    
    def create_widget(self, parent):       
        from voter.voter_widget import voterWidget 
        self.w = voterWidget(parent, self.send_vote, self.logger)
        return self.w
    
    def process_event(self, cmd, value, ip, member_info, _prep):
        if cmd == "HELO_VOTE":
            if self.w is None:
                self.logger.error("Voter: Vote cannot be processed")
                return
            vote = json.loads(value)
            if vote.has_key("time") and vote.has_key("place"):
                self.add_vote(member_info[u"ID"], vote["place"], vote["time"])
                displayNotification("New Vote", "%s voted" % get_peers().getDisplayedPeerName(pIP=ip), self.logger)
            else:
                self.logger.error("Voter: Vote does not look valid: %s", value)
        
    # todo: rename ip=>id
    def add_vote(self, ip, vote_place, vote_time):
        if self.ip2vote.has_key(ip):
            # member has already voted, revoke old vote
            old_vote = self.ip2vote[ip]
            self.vote_count[ old_vote ] -= 1
            if self.w is not None:
                self.w.update_table_row(old_vote[0],
                                   old_vote[1],
                                   self.vote_count[ old_vote])
            if self.vote_count[ old_vote ] == 0:
                self.vote_count.pop(old_vote)
            
        self.ip2vote[ip] = (vote_place, vote_time)
        if self.vote_count.has_key(self.ip2vote[ip]):
            self.vote_count[ self.ip2vote[ip] ] += 1
            if self.w is not None:
                self.w.update_table_row(vote_place,
                                   vote_time,
                                   self.vote_count[ self.ip2vote[ip] ])
        else:
            self.vote_count[ self.ip2vote[ip] ] = 1  
            if self.w is not None:
                self.w.add_place_to_dropdown(vote_place)  
                self.w.add_table_row(vote_place, vote_time)  
            
    
    def send_vote(self, place, stime):
        vote_call = "HELO_VOTE " + json.dumps({"place": place, "time": unicode(stime.toString("hh:mm"))})
        get_server().call(vote_call)
        
        etime = stime.addSecs(60 * 30)
        get_server().getController().changeNextLunchTime(stime.toString("hh:mm"), etime.toString("hh:mm"))

if __name__ == "__main__":
    v = voter()
    v.run_in_window()
