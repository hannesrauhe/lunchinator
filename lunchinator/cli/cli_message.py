from lunchinator.cli import LunchCLIModule
from lunchinator import get_server, log_exception

class CLIMessageHandling(LunchCLIModule):
    def do_send(self, args):
        """
        Send a message.
        Usage: send <message>                             - Send message to all members
               send <message> <member1> [<member2> [...]] - Send message to specific members 
        """
        if len(args) == 0:
            self.printHelp("send")
            return False
        
        args = self.getArguments(args)
        message = args.pop(0)
        try:
            get_server().call(message, peerIPs=self.getHostList(args))
        except:
            log_exception("Error sending")
        
    def complete_send(self, text, line, begidx, endidx):
        if self.getArgNum(text, line, begidx, endidx)[0] > 1:
            # message is already entered, complete hostnames
            return self.completeHostnames(text, line, begidx, endidx)

    def do_call(self, args):
        """
        Call for lunch.
        Usage: call                             - Call all members
               call <member1> [<member2> [...]] - Call specific members 
        """
        args = args.decode('utf-8')
        args = self.getArguments(args)
        try:
            get_server().call("lunch", peerIPs=self.getHostList(args))
        except:
            log_exception("Error calling")
        
    def complete_call(self, text, line, begidx, endidx):
        return self.completeHostnames(text, line, begidx, endidx)
    