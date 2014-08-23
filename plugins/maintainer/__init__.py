from lunchinator.plugin import iface_gui_plugin
from lunchinator import get_settings
import os
from lunchinator.lunch_peers import LunchPeers

class maintainer(iface_gui_plugin):
    def __init__(self):
        super(maintainer, self).__init__()
        self.recorded_reports = []
        self.dbPluginErrorPrinted = False
        self.w = None
        
    def activate(self):
        iface_gui_plugin.activate(self)  
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def create_widget(self, parent):
        from maintainer.maintainer_gui import maintainer_gui
        iface_gui_plugin.create_widget(self, parent)
        self.w = maintainer_gui(parent, self.logger)
        
        return self.w
    
    def destroy_widget(self):
        if self.w != None:
            self.w.destroy_widget()
        iface_gui_plugin.destroy_widget(self)
            
    def add_menu(self,menu):
        pass
    
    def process_event(self, cmd, value, ip, peerInfo, _prep):
        if cmd.startswith("HELO_LOGFILE"):
            if self.w == None:
                return
            from lunchinator.datathread.dt_qthread import DataReceiverThread
            #someone will send me his logfile on tcp
            values = value.split()
            file_size=int(values[0])
            tcp_port = 0
            if len(values) > 1:
                tcp_port = int(values[1])
            
            pID = peerInfo.get(LunchPeers.PEER_ID_KEY, ip)
            
            logDir = os.path.join(get_settings().get_main_config_dir(), "logs", pID)
            if not os.path.exists(logDir):
                os.makedirs(logDir)
            
            if cmd.startswith("HELO_LOGFILE_TGZ"):
                file_name= os.path.join(logDir, "tmp.tgz")
            else:
                file_name= os.path.join(logDir, "tmp.log")
            
            dr = DataReceiverThread.receiveSingleFile(ip, file_name, file_size, tcp_port, self.logger, "log%s"%ip, parent=self.w)
            dr.successfullyTransferred.connect(self.w.membersWidget.cb_log_transfer_success)
            dr.errorOnTransfer.connect(self.w.membersWidget.cb_log_transfer_error)
            dr.finished.connect(dr.deleteLater)
            dr.start()
            
if __name__ == '__main__':
    def logSomething():
        from lunchinator.log import getCoreLogger
        getCoreLogger().info("foo")
        
    m = maintainer()
    m.run_in_window(callAfterCreate=logSomething)
