import subprocess,sys,ctypes
from lunchinator import log_exception, log_warning, log_debug,\
    get_settings, log_error
import os
import threading
import contextlib
from datetime import datetime
import json

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
    if msg == None:
        msg = u""
    myPlatform = getPlatform()
    try:
        if myPlatform == PLATFORM_LINUX:
            subprocess.call(["notify-send","--icon="+icon, name, msg])
        elif myPlatform == PLATFORM_MAC:
            fh = open(os.path.devnull,"w")
            exe = getBinary("terminal-notifier", "bin")
            if not exe:
                log_warning("terminal-notifier not found.")
                return
            
            call = [exe, "-title", "Lunchinator: %s" % name, "-message", msg]
            if False and AttentionGetter.getInstance().existsBundle: # no sender until code signing is fixed (probably never)
                call.extend(["-sender", _LUNCHINATOR_BUNDLE_IDENTIFIER])
                
            log_debug(call)
            subprocess.call(call, stdout=fh, stderr=fh)
        elif myPlatform == PLATFORM_WINDOWS:
            from lunchinator import get_server
            if hasattr(get_server().controller, "statusicon"):
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
    from lunchinator import get_server
    from PyQt4.QtCore import QObject
    if isinstance(get_server().controller, QObject):
        return get_server().controller
    elif isinstance(qtParent, QObject):
        return qtParent
    raise Exception("Could not find a valid QObject instance")
    
def processPluginCall(ip, call):
    from lunchinator import get_server
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
    try:
        if altLocation:
            gbinary = get_settings().get_resource(altLocation, name)
    except:
        altLocation=""
         
    if not altLocation:
        gbinary = which(name)
    
    if not gbinary or not os.path.isfile(gbinary):
        return None   
    
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
    gbinary = getBinary("gpg", "bin")
    if not gbinary:
        log_error("GPG not found")
        return None, None
    
    ghome = os.path.join(get_settings().get_main_config_dir(),"gnupg")
    
    try:
        gpg = None
        if getPlatform() == PLATFORM_WINDOWS:
            gpg = GPG("\""+gbinary+"\"",ghome)
        else:
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

def getTimeDelta(end):
    """
    calculates the correlation of now and the specified time
    positive value: now is before time, milliseconds until time
    negative value: now is after time, milliseconds after time
    Returns None if the time format is invalid. 
    """
    try:
        from lunchinator.lunch_settings import lunch_settings
        
        try:
            end = datetime.strptime(end, lunch_settings.LUNCH_TIME_FORMAT)
        except ValueError:
            log_debug("Unsupported time format:", end)
            return None
        
        # ignore begin
        now = datetime.now()
        end = end.replace(year=now.year, month=now.month, day=now.day)
        
        td = end - now
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 3
    
    except:
        log_exception("don't know how to handle time span")
        return None
    

def getTimeDifference(begin, end):
    """
    calculates the correlation of now and the specified lunch dates
    negative value: now is before begin, seconds until begin
    positive value: now is after begin but before end, seconds until end
     0: now is after end
    toEnd = True: always calculate seconds until end
    Returns None if the time format is invalid. 
    """
    try:
        from lunchinator.lunch_settings import lunch_settings
        
        try:
            end = datetime.strptime(end, lunch_settings.LUNCH_TIME_FORMAT)
        except ValueError:
            log_debug("Unsupported time format:", end)
            return None
        
        try:
            begin = datetime.strptime(begin, lunch_settings.LUNCH_TIME_FORMAT)
        except ValueError:
            # this is called repeatedly, so only debug
            log_debug("Unsupported time format:", begin)
            return None
        
        now = datetime.now()
        begin = begin.replace(year=now.year, month=now.month, day=now.day)
        end = end.replace(year=now.year, month=now.month, day=now.day)
        
        if now < begin:
            # now is before begin
            td = begin - now
            millis = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 3
            return -1 if millis == 0 else -millis
        elif now < end:
            td = end - now
            millis = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 3
            return 1 if millis == 0 else millis
        else:
            # now is after end
            return 0
    except:
        log_exception("don't know how to handle time span")
        return None
    
def getApplicationBundle():
    """Determines the path to the Mac application bundle"""
    path = os.path.abspath(sys.argv[0])
    while not path.endswith(".app"):
        newPath = os.path.dirname(path)
        if newPath == path:
            path = None
            break
        path = newPath
    
    if path == None or not os.path.exists(os.path.join(path, "Contents", "MacOS", "Lunchinator")):
        return None
    return path

def spawnProcess(args):
    if getPlatform() in (PLATFORM_LINUX, PLATFORM_MAC):
        #somehow fork() is not safe on Mac OS. I guess this will do fine on Linux, too. 
        subprocess.Popen(['nohup'] + args, close_fds=True)
    elif getPlatform() == PLATFORM_WINDOWS:
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
    else:
        raise NotImplementedError("Process spawning not implemented for your OS.")

def _getStartCommand():
    if getPlatform() == PLATFORM_MAC:
        # Git or Application bundle?
        bundlePath = getApplicationBundle()
        if bundlePath:
            return ["open", bundlePath]
    
    if getPlatform() in (PLATFORM_MAC, PLATFORM_LINUX):
        args = ["nohup", sys.executable]
        args.extend(sys.argv)
        return args
    elif getPlatform() == PLATFORM_WINDOWS:
        return ["pythonw", os.path.join(get_settings().get_main_package_path(), "start_lunchinator.py")]
    else:
        log_error("Restart not yet implemented for your OS.")
            
    return None
    
def _getPythonInterpreter():
    # sys.executable does not always return the python interpreter
    if getPlatform() == PLATFORM_WINDOWS:
        return "pythonw"
    return which("python")
    
def restartWithCommands(commands):
    """
    Restart Lunchinator and execute commands in background while it is stopped.
    commands: lunchinator.commands.Commands instance
    """
    from lunchinator import get_server
    try:
        startCmd = _getStartCommand()
        args = [_getPythonInterpreter(), get_settings().get_resource("bin", "restart.py"),
                "--lunchinator-path", get_settings().get_main_package_path(),
                "--start-cmd", json.dumps(startCmd),
                "--pid", str(os.getpid())]
        if commands != None:
            args.extend(["--commands", commands.toString()])
        
        spawnProcess(args)
    except:
        log_exception("Error in stopWithCommands")
        return
    get_server().get_controller().shutdown()
    
def restart():
    """Restarts the Lunchinator"""
    restartWithCommands(None)

