from lunchinator.iface_plugins import iface_general_plugin
from privacy_gui.gui import PrivacyGUI
from lunchinator.privacy import PrivacySettings

class privacy(iface_general_plugin):
    def __init__(self):
        super(privacy, self).__init__()
        self._ui = None
        self._modified = False
        self.force_activation = True
        self.hidden_options = {u"json" : u"{}"}
        
    def activate(self):
        iface_general_plugin.activate(self)
        PrivacySettings.initialize(self.hidden_options[u"json"])
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)

    def create_options_widget(self, parent):
        self._ui = PrivacyGUI(parent)
        return self._ui  
    
    def get_displayed_name(self):
        return u"Privacy"
    
    def discard_changes(self):
        PrivacySettings.get().discard()
        
    def save_options_widget_data(self, **_kwargs):
        PrivacySettings.get().save()
        self.set_hidden_option(u"json", PrivacySettings.get().getJSON(), convert=False)
    
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
        
        def hasCategories(self):
            return True
        
        def getCategoryFromMessage(self, _msgData):
            return u"Category 1"
    
    w = privacy()
    testAction = TestAction()
    testAction._pluginObject = w
    testAction._pluginName = "Test Plugin"
    PeerActions.get()._peerActions["Test Plugin"] = [testAction]
    w.run_options_widget()
    PrivacySettings.get().save()
    print PrivacySettings.get()._settings