from lunchinator import convert_string, get_settings
from lunchinator.plugin import iface_general_plugin
from lunchinator.log.lunch_logger import setLoggingLevel, setGlobalLoggingLevel
    
class plugin_repositories(iface_general_plugin):
    def __init__(self):
        super(plugin_repositories, self).__init__()
        
    def get_displayed_name(self):
        return u"Logging Level Settings"
    
    def activate(self):
        iface_general_plugin.activate(self)
        
    def deactivate(self):
        iface_general_plugin.deactivate(self)
        
    def has_options_widget(self):
        return True
        
    def create_options_widget(self, parent):
        from logging_level_settings.logging_level_gui import LoggingLevelGUI
        self._ui = LoggingLevelGUI(self.logger, parent)
        self._ui.resizeColumns()
        return self._ui
        
    def discard_changes(self):
        self._ui.reset()
        
    def _getLevelFromText(self, text):
        level = None
        from logging_level_settings.logging_level_gui import LogLevelModel
        for aLevel, aLevelText in LogLevelModel._LEVEL_TEXT.iteritems():
            if aLevelText == text:
                level = aLevel
        return level
    
    def save_options_widget_data(self, **_kwargs):
        from PyQt4.QtCore import Qt
        from logging_level_settings.logging_level_gui import LogLevelModel
        get_settings().set_logging_level(self._ui.getGlobalLevelText())
        
        model = self._ui.getModel() 
        for row in xrange(model.rowCount()):
            loggerName = convert_string(model.item(row, LogLevelModel.NAME_COLUMN).data(LogLevelModel.KEY_ROLE).toString())
            levelText = convert_string(model.item(row, LogLevelModel.LEVEL_COLUMN).data(Qt.DisplayRole).toString())
            level = self._getLevelFromText(levelText)
            setLoggingLevel(loggerName, level)
    
if __name__ == '__main__':
    from lunchinator.plugin import iface_gui_plugin
    w = plugin_repositories()
    w.run_options_widget()
