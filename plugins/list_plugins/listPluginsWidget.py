from ui_plugins import Ui_Plugins
from PyQt4.Qt import QWidget

class listPluginsWidget(QWidget):
    def __init__(self, parent, p_info):
        super(listPluginsWidget, self).__init__(parent)
        self.p_info = p_info
        self.ui = Ui_Plugins()
        self.ui.setupUi(self)
        for p_name in p_info.keys():
            self.ui.pluginView.addItem(p_name)
        self.ui.pluginView.setCurrentRow(0)
            
    def plugin_selected(self, current, old):
        p = self.p_info[str(current.text())]
        self.ui.authorLabel.setText("Author: "+p["author"])
        self.ui.descriptionlabel.setText(p["description"])
        for req in p["requirements"]:
            self.ui.requirementsView.addItem(req)