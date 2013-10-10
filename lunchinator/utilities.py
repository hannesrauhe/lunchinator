import subprocess,sys,ctypes
from lunchinator import log_exception, get_server, log_warning,\
    log_debug
import os
from lunchinator.iface_plugins import iface_called_plugin, iface_gui_plugin
import threading

PLATFORM_OTHER = -1
PLATFORM_LINUX = 0
PLATFORM_MAC = 1
PLATFORM_WINDOWS = 2

def getPlatform():
    if "linux" in sys.platform:
        return PLATFORM_LINUX
    elif "darwin" in sys.platform:
        return PLATFORM_MAC
    elif "win32" in sys.platform:
        return PLATFORM_WINDOWS
    else:
        return PLATFORM_OTHER

def displayNotification(name,msg,icon):
    myPlatform = getPlatform()
    try:
        if myPlatform == PLATFORM_LINUX:
            subprocess.call(["notify-send","--icon="+icon, name, msg])
        elif myPlatform == PLATFORM_MAC:
            fh = open(os.path.devnull,"w")
            subprocess.call(["terminal-notifier", "-title", "Lunchinator: %s" % name, "-message", msg], stdout=fh, stderr=fh)
        elif myPlatform == PLATFORM_WINDOWS:
            _drawAttentionWindows()
    except:
        log_exception("error displaying notification")
        
class AttentionGetter(object):
    _instance = None
    
    class AttentionThread(threading.Thread):
        def __init__(self, audioFile):
            super(AttentionGetter.AttentionThread, self).__init__()
            self._audioFile = audioFile
        
        def run(self):        
            myPlatform = getPlatform()
            if myPlatform == PLATFORM_LINUX:
                _drawAttentionLinux(self._audioFile)
            elif myPlatform == PLATFORM_MAC:
                _drawAttentionMac(self._audioFile)
            elif myPlatform == PLATFORM_WINDOWS:
                _drawAttentionWindows()
    
    def __init__(self):
        super(AttentionGetter, self).__init__()
        self.attentionThread = None
        
    @classmethod
    def getInstance(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
    
    def drawAttention(self, audioFile):
        if self.attentionThread != None and self.attentionThread.isAlive():
            # someone is already drawing attention at the moment
            log_debug("Drawing attention is already in progress.")
            return
        else:
            log_debug("Starting new attention thread.")
            self.attentionThread = self.AttentionThread(audioFile)
            self.attentionThread.start()
        
def drawAttention(audioFile):
    AttentionGetter.getInstance().drawAttention(audioFile)
        
def _drawAttentionLinux(audioFile):       
    try:
        subprocess.call(["eject", "-T", "/dev/cdrom"])
    except:
        log_exception("notify error: eject error (open)")
    
    try:
        subprocess.call(["play", "-q", audioFile])    
    except:
        log_exception("notify error: sound error")

    try:
        subprocess.call(["eject", "-T", "/dev/cdrom"])
    except:
        log_exception("notify error: eject error (close)")
        
def _drawAttentionMac(audioFile):      
    try:
        subprocess.call(["drutil", "tray", "eject"])
    except:
        log_exception("notify error: eject error (open)")
         
    try:
        subprocess.call(["afplay", audioFile])    
    except:
        log_exception("notify error: sound error")
         
    try:
        subprocess.call(["drutil", "tray", "close"])
    except:
        log_exception("notify error: eject error (close)")

def _drawAttentionWindows():    
    try:
        ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
    except:
        log_exception("notify error: eject error (open)")
    try:
        ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
    except:
        log_exception("notify error: eject error (close)")

def getValidQtParent():
    from PyQt4.QtCore import QObject
    if isinstance(get_server().controller, QObject):
        return get_server().controller
    raise Exception("Could not find a valid QObject instance")
    
def processPluginCall(ip, call):
    member_info = {}
    if get_server().member_info.has_key(ip):
        member_info = get_server().member_info[ip]
    # called also contains gui plugins
    for pluginInfo in get_server().plugin_manager.getPluginsOfCategory("called")+get_server().plugin_manager.getPluginsOfCategory("gui"):
        if not (isinstance(pluginInfo.plugin_object, iface_called_plugin) or  isinstance(pluginInfo.plugin_object, iface_gui_plugin)):
            log_warning("Plugin '%s' is not a called/gui plugin" % pluginInfo.name)
            continue
        if pluginInfo.plugin_object.is_activated:
            try:
                call(pluginInfo.plugin_object, ip, member_info)
            except:
                log_exception(u"plugin error in %s while processing event" % pluginInfo.name)