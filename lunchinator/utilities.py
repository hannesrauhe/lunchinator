import subprocess,sys,ctypes
from lunchinator import log_exception, get_server, log_warning, log_debug,\
    get_settings, log_error
import os
import threading
import contextlib

PLATFORM_OTHER = -1
PLATFORM_LINUX = 0
PLATFORM_MAC = 1
PLATFORM_WINDOWS = 2

_LUNCHINATOR_BUNDLE_IDENTIFIER = "hannesrauhe.lunchinator"

def getPlatform():
    if "linux" in sys.platform:
        return PLATFORM_LINUX
    elif "darwin" in sys.platform:
        return PLATFORM_MAC
    elif "win32" in sys.platform:
        return PLATFORM_WINDOWS
    else:
        return PLATFORM_OTHER

def checkBundleIdentifier(ident):
    res = subprocess.call([get_settings().get_resource('bin', 'check_bundle_identifier.sh'), ident])
    return res == 1

# TODO: message groups for notification center
def displayNotification(name,msg,icon=None):
    myPlatform = getPlatform()
    try:
        if myPlatform == PLATFORM_LINUX:
            subprocess.call(["notify-send","--icon="+icon, name, msg])
        elif myPlatform == PLATFORM_MAC:
            fh = open(os.path.devnull,"w")
            exe = getBinary("terminal-notifier")
            if not exe:
                return
            
            call = [exe, "-title", "Lunchinator: %s" % name, "-message", msg]
            if False and AttentionGetter.getInstance().existsBundle: # no sender until code signing is fixed (probably never)
                call.extend(["-sender", _LUNCHINATOR_BUNDLE_IDENTIFIER])
                
            log_debug(call)
            subprocess.call(call, stdout=fh, stderr=fh)
        elif myPlatform == PLATFORM_WINDOWS:
            get_server().controller.statusicon.showMessage(name,msg)
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
                _drawAttentionWindows(self._audioFile)
    
    def __init__(self):
        super(AttentionGetter, self).__init__()
        self.attentionThread = None
        if getPlatform() == PLATFORM_MAC:
            self.existsBundle = checkBundleIdentifier(_LUNCHINATOR_BUNDLE_IDENTIFIER)
        
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

def _drawAttentionWindows(audioFile):    
    try:
        ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
    except:
        log_exception("notify error: eject error (open)")
    try:
        from PyQt4.QtGui import QSound
        q = QSound(audioFile)
        q.play()
    except:        
        log_exception("notify error: sound")
        
    try:
        ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
    except:
        log_exception("notify error: eject error (close)")

qtParent = None 

def setValidQtParent(parent):
    global qtParent
    qtParent = parent

def getValidQtParent():
    from PyQt4.QtCore import QObject
    if isinstance(get_server().controller, QObject):
        return get_server().controller
    elif isinstance(qtParent, QObject):
        return qtParent
    raise Exception("Could not find a valid QObject instance")
    
def processPluginCall(ip, call):
    if not get_server().get_plugins_enabled():
        return
    from lunchinator.iface_plugins import iface_called_plugin, iface_gui_plugin
    member_info = {}
    if get_server().get_peer_info().has_key(ip):
        member_info = get_server().get_peer_info()[ip]
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
                
def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep) + ["/usr/local/bin"]:
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def getBinary(name, altLocation = ""):
    if getPlatform() == PLATFORM_WINDOWS:
        name += ".exe"
        
    gbinary = which(name)
    if not gbinary:
        gbinary = get_settings().get_resource(altLocation, name)
    if not os.path.isfile(gbinary):
        return None   
    
    if getPlatform() == PLATFORM_WINDOWS:
        gbinary = "\""+gbinary+"\""
    return os.path.realpath(gbinary)

def _findLunchinatorKeyID(gpg, secret):
    # use key from keyring as default
    for key in gpg.list_keys(secret):
        for uid in key['uids']:
            if 'info@lunchinator.de' in uid:
                return key['keyid']
    return None

def getGPG(secret=False):
    """ Returns tuple (GPG instance, keyid) """
    
    from gnupg import GPG
    gbinary = getBinary("gpg", "gnupg")
    if not gbinary:
        log_error("GPG not found")
        return None, None
    
    ghome = os.path.join(get_settings().get_main_config_dir(),"gnupg")
    
    try:
        gpg = GPG(gbinary,ghome)
        if not gpg.encoding:
            gpg.encoding = 'utf-8'
    except Exception, e:
        log_exception("GPG not working: "+str(e))
        return None, None
    
    # use key from keyring as default
    keyid = _findLunchinatorKeyID(gpg, secret)
    
    if keyid == None:
        # no key in keyring, try to import from file
        path = None
        if secret:
            path = os.path.join(ghome, "lunchinator_pub_sec_0x17F57DC2.asc")
        else:
            path = get_settings().get_resource("lunchinator_pub_0x17F57DC2.asc")
                
        if not os.path.isfile(path):
            log_error("Key file not found:", path)
            return None, None
        with contextlib.closing(open(path,"r")) as keyf:
            gpg.import_keys(keyf.read())
            keyid = _findLunchinatorKeyID(gpg, secret)
    
    return gpg, keyid

