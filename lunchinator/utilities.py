import subprocess, sys, os, contextlib, json, shutil, socket
from datetime import datetime, timedelta
from lunchinator import log_exception, log_warning, log_debug, \
    get_settings, log_error

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
def displayNotification(name, msg, icon=None):
    if msg == None:
        msg = u""
    myPlatform = getPlatform()
    try:
        if myPlatform == PLATFORM_LINUX:
            if icon == None:
                icon = ""
            subprocess.call(["notify-send","--icon="+icon, name, msg])
        elif myPlatform == PLATFORM_MAC:
            fh = open(os.path.devnull,"w")
            exe = getBinary("terminal-notifier", "bin")
            if not exe:
                log_warning("terminal-notifier not found.")
                return
            
            call = [exe, "-title", "Lunchinator: %s" % name, "-message", msg]
            if False and checkBundleIdentifier(_LUNCHINATOR_BUNDLE_IDENTIFIER): # no sender until code signing is fixed (probably never)
                call.extend(["-sender", _LUNCHINATOR_BUNDLE_IDENTIFIER])
                
            log_debug(call)
            subprocess.call(call, stdout=fh, stderr=fh)
        elif myPlatform == PLATFORM_WINDOWS:
            from lunchinator import get_server
            if hasattr(get_server().controller, "statusicon"):
                get_server().controller.statusicon.showMessage(name,msg)
    except:
        log_exception("error displaying notification")
        
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
    
def processPluginCall(ip, call, newPeer, fromQueue):
    from lunchinator import get_peers, get_plugin_manager
    if not get_settings().get_plugins_enabled():
        return
    from lunchinator.iface_plugins import iface_called_plugin, iface_gui_plugin
    
    member_info = get_peers().getPeerInfo(pIP=ip)
    
    # called also contains gui plugins
    for pluginInfo in get_plugin_manager().getPluginsOfCategory("called")+get_plugin_manager().getPluginsOfCategory("gui"):
        if not (isinstance(pluginInfo.plugin_object, iface_called_plugin) or \
                isinstance(pluginInfo.plugin_object, iface_gui_plugin)):
            log_warning("Plugin '%s' is not a called/gui plugin" % pluginInfo.name)
            continue
        if pluginInfo.plugin_object.is_activated:
            try:
                if (pluginInfo.plugin_object.processes_events_immediately() and not fromQueue) or \
                   (not pluginInfo.plugin_object.processes_events_immediately() and not newPeer):
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

# TODO not used anymore. May be removed.    
'''for the external IP a connection to someone has to be opened briefly
   therefore a list of possible peers is needed'''
def determineOwnIP(peers):
    if 0 == len(peers):
        log_debug("Cannot determine IP if there is no peer given")
        return None
    
    own_ip = None
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)      
    for m in peers:
        try:
            # connect to UDF discard port 9
            s.connect((m, 9))
            own_ip = unicode(s.getsockname()[0])
            break
        except:
            log_debug("While getting own IP, problem to connect to", m)
            continue
    if own_ip:
        log_debug("Found my IP:", own_ip)
    s.close()
    return own_ip

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

def msecUntilNextMinute():
    now = datetime.now()
    nextMin = now.replace(second=0, microsecond=0) + timedelta(minutes=1, seconds=1)
    td = nextMin - now
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 3
    
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
        fh = open(os.path.devnull, "w")
        subprocess.Popen(['nohup'] + args, close_fds=True, stdout=fh, stderr=fh)
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
        # copy restart script to safe place
        shutil.copy(get_settings().get_resource("bin", "restart.py"), get_settings().get_main_config_dir())
        
        startCmd = _getStartCommand()
        args = [_getPythonInterpreter(), get_settings().get_config("restart.py"),
                "--lunchinator-path", get_settings().get_main_package_path(),
                "--start-cmd", json.dumps(startCmd),
                "--pid", str(os.getpid())]
        if commands != None:
            args.extend(["--commands", commands.toString()])
        
        spawnProcess(args)
    except:
        log_exception("Error in stopWithCommands")
        return
    if get_server().getController():
        get_server().getController().shutdown()
    
def restart():
    """Restarts the Lunchinator"""
    restartWithCommands(None)

