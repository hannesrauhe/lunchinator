from yapsy.IPlugin import IPlugin
import gtk,types

class iface_plugin(IPlugin):
    options = None
    option_widgets = {}
    
    def activate(self):
        """
        Call the parent class's acivation method
        """
        IPlugin.activate(self)
        self.read_options_from_file()
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        IPlugin.deactivate(self)
        
    def read_options_from_file(self):
        if not self.options:
            return
        for o,v in self.options.iteritems():
            if self.hasConfigOption(o):
                new_v = self.getConfigOption(o)
                try:
                    if type(v)==types.IntType:
                        self.options[o] = int(new_v)
                    elif type(v)==types.BooleanType:
                        self.options[o] = bool(new_v)
                    elif type(v)==types.StringType:
                        self.options[o] = new_v
                    else:
                        print "type of value",o,v,"not supported, using default"
                except:
                    print "could not convert value of",o,"from config to type",type(v),"(",new_v,") using default"
                    
        
    def create_options_widget(self):
        if not self.options:
            return None
        t = gtk.Table(len(self.options),2,False)
        i=0
        for o,v in self.options.iteritems():
            e = ""
            if type(v)==types.IntType:
                adjustment = gtk.Adjustment(value=v, lower=0, upper=1000000, step_incr=1, page_incr=0, page_size=0)
                e = gtk.SpinButton(adjustment)
            elif type(v)==types.BooleanType:
                e = gtk.CheckButton()
                e.set_active(v)
            else:
                e = gtk.Entry()
                e.set_text(v)
            t.attach(gtk.Label(o),0,1,i,i+1)
            t.attach(e,1,2,i,i+1)
            i+=1
            self.option_widgets[o]=e
        return t
    
    def save_options_widget_data(self):
        if not self.option_widgets:
            return
        for o,e in self.option_widgets.iteritems():
            v = self.options[o]
            new_v = v
            if type(v)==types.IntType:
                new_v = e.get_value_as_int()
            elif type(v)==types.BooleanType:
                new_v = e.get_active()
            else:
                new_v = e.get_text()
            if new_v!=v:
                self.options[o]=new_v
                self.setConfigOption(o,str(new_v))
        self.discard_options_widget_data()
    
    def discard_options_widget_data(self):
        self.option_widgets = {}
        
class iface_gui_plugin(iface_plugin):    
    def activate(self):
        """
        Call the parent class's acivation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)
        
    def create_widget(self):
        return gtk.Label("The plugin should show its content here")
    
    def add_menu(self,menu):
        pass

class iface_called_plugin(iface_plugin):    
    def activate(self):
        """
        Call the parent class's acivation method
        """
        iface_plugin.activate(self)
        return


    def deactivate(self):
        """
        Just call the parent class's method
        """
        iface_plugin.deactivate(self)
        
    def process_message(self,msg,ip,member_info):
        pass
        
    def process_lunch_call(self,msg,ip,member_info):
        pass
        
    def process_event(self,cmd,value,ip,member_info):
        pass