from lunchinator.iface_plugins import iface_general_plugin
from privacy.privacy_gui import PrivacyGUI

class privacy(iface_general_plugin):
    def __init__(self):
        super(privacy, self).__init__()
        self._ui = None
        self._modified = False
        self.force_activation = True
        
    def activate(self):
        iface_general_plugin.activate(self)
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)
        
    def create_options_widget(self, parent):
        self._ui = PrivacyGUI(parent)
        return self._ui  
    
    def get_displayed_name(self):
        return u"Privacy"
    
    def discard_changes(self):
        # TODO
        pass
        
    def save_options_widget_data(self, **_kwargs):
        # TODO
        pass
    
if __name__ == '__main__':
    from lunchinator.peer_actions import PeerAction, PeerActions
    from lunchinator.iface_plugins import iface_gui_plugin
    
    class TestAction(PeerAction):
        def getName(self):
            return "Test Action"
        
        def getMessagePrefix(self):
            return "TEST"
        
        def getPrivacyCategories(self):
            return (u"Category 1", u"Category 2")
    
    PeerActions.get()._peerActions["Test Plugin"] = [TestAction()]
    w = privacy()
    w.run_options_widget()
