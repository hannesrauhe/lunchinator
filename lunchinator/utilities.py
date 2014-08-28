import subprocess, sys, os, contextlib, json, shutil, time
from datetime import datetime, timedelta 
from time import mktime, strftime
from lunchinator import get_settings
from lunchinator.log import getCoreLogger
import locale
import platform
from tempfile import NamedTemporaryFile
import itertools
import string
import errno
import sys
from pkg_resources import get_distribution, ResolutionError,\
    DistributionNotFound, VersionConflict

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

def isPyinstallerBuild():
    frozen = getattr(sys, 'frozen', '')
    return frozen

def checkBundleIdentifier(ident):
    res = subprocess.call([get_settings().get_resource('bin', 'check_bundle_identifier.sh'), ident])
    return res == 1

def _mustScaleNotificationIcon():
    if getPlatform() == PLATFORM_LINUX:
        return platform.linux_distribution()[0].startswith("SUSE Linux Enterprise")

# TODO: message groups for notification center
def displayNotification(name, msg, logger, icon=None):
    if msg == None:
        msg = u""
    myPlatform = getPlatform()
    try: 
        from lunchinator import get_server
        if not get_server().has_gui():
            print time.strftime("%Y-%m-%d %H:%M"),name, msg
    except:
        print time.strftime("%Y-%m-%d %H:%M"),name, msg
    
    try:
        if myPlatform == PLATFORM_LINUX:
            fileToClose = None
            if icon is None or not os.path.exists(icon):
                icon = ""
            elif _mustScaleNotificationIcon():
                import Image
                im = Image.open(icon)
                im.thumbnail((64,64), Image.ANTIALIAS)
                fileToClose = NamedTemporaryFile(suffix='.png', delete=True)
                im.save(fileToClose, "PNG")
                fileToClose.flush()
                icon = fileToClose.name
            subprocess.call(["notify-send","--icon="+icon, name, msg])
            if fileToClose is not None:
                fileToClose.close()
        elif myPlatform == PLATFORM_MAC:
            fh = open(os.path.devnull,"w")
            exe = getBinary("terminal-notifier", "bin")
            if not exe:
                logger.warning("terminal-notifier not found.")
                return
            
            call = [exe, "-title", "Lunchinator: %s" % name, "-message", msg]
            if False and checkBundleIdentifier(_LUNCHINATOR_BUNDLE_IDENTIFIER): # no sender until code signing is fixed (probably never)
                call.extend(["-sender", _LUNCHINATOR_BUNDLE_IDENTIFIER])
                
            logger.debug(call)
            try:
                subprocess.call(call, stdout=fh, stderr=fh)
            except OSError as e:
                if e.errno == errno.EINVAL:
                    logger.warning("Ignoring invalid value on Mac")
                else:
                    raise
            except:
                logger.exception("Error calling %s", call)
        elif myPlatform == PLATFORM_WINDOWS:
            from lunchinator import get_server
            if hasattr(get_server().controller, "statusicon"):
                get_server().controller.statusicon.showMessage(name,msg)
    except:
        logger.exception("error displaying notification")
        
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
    
def canUseBackgroundQThreads():
    try:
        from PyQt4.QtCore import PYQT_VERSION_STR
        from distutils.version import LooseVersion
        # TODO I have no clue from which version on it actually works.
        return LooseVersion(PYQT_VERSION_STR) > LooseVersion("4.7.2")
    except:
        return False
                
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

lunch_gpg = None

def getGPG():
    global lunch_gpg
    if not lunch_gpg:
        from gnupg import GPG
        gbinary = getBinary("gpg", "bin")
        if not gbinary:
            raise Exception("GPG not found")
        
        ghome = os.path.join(get_settings().get_main_config_dir(),"gnupg")
        
        if not locale.getpreferredencoding():
            # Fix for GnuPG on Mac
            # TODO will this work on systems without English locale?
            os.putenv("LANG", "en_US.UTF-8")
        
        if not locale.getpreferredencoding():
            # Fix for GnuPG on Mac
            # TODO will this work on systems without English locale?
            os.putenv("LANG", "en_US.UTF-8")
        
        try:
            if getPlatform() == PLATFORM_WINDOWS:
                lunch_gpg = GPG("\""+gbinary+"\"",ghome)
            else:
                lunch_gpg = GPG(gbinary,ghome)
            if not lunch_gpg.encoding:
                lunch_gpg.encoding = 'utf-8'
        except Exception, e:
            raise Exception("GPG not working: "+str(e))

    return lunch_gpg

def getGPGandKey(secret=False):
    """ Returns tuple (GPG instance, keyid) """
    gpg = getGPG()
    
    # use key from keyring as default    
    ghome = os.path.join(get_settings().get_main_config_dir(),"gnupg")
    keyid = _findLunchinatorKeyID(gpg, secret)
    
    if keyid == None:
        # no key in keyring, try to import from file
        path = None
        if secret:
            path = os.path.join(ghome, "lunchinator_pub_sec_0x17F57DC2.asc")
        else:
            path = get_settings().get_resource("lunchinator_pub_0x17F57DC2.asc")
                
        if not os.path.isfile(path):
            raise Exception("Key file not found: %s"%path)
        with contextlib.closing(open(path,"r")) as keyf:
            gpg.import_keys(keyf.read())
            keyid = _findLunchinatorKeyID(gpg, secret)
    
    return gpg, keyid

def getTimeDelta(end, logger):
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
            logger.debug("Unsupported time format: %s", end)
            return None
        
        # ignore begin
        now = datetime.now()
        end = end.replace(year=now.year, month=now.month, day=now.day)
        
        td = end - now
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 3
    
    except:
        logger.exception("don't know how to handle time span")
        return None
    

def getTimeDifference(begin, end, logger):
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
            logger.debug("Unsupported time format: %s", end)
            return None
        
        try:
            begin = datetime.strptime(begin, lunch_settings.LUNCH_TIME_FORMAT)
        except ValueError:
            # this is called repeatedly, so only debug
            logger.debug("Unsupported time format: %s", begin)
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
        logger.exception("don't know how to handle time span")
        return None

def msecUntilNextMinute():
    now = datetime.now()
    nextMin = now.replace(second=0, microsecond=0) + timedelta(minutes=1, milliseconds=100)
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

def spawnProcess(args, logger):
    logger.debug("spawning process: %s", args)
    if getPlatform() in (PLATFORM_LINUX, PLATFORM_MAC):
        #somehow fork() is not safe on Mac OS. I guess this will do fine on Linux, too. 
        fh = open(os.path.devnull, "w")
        subprocess.Popen(['nohup'] + args, close_fds=True, stdout=fh, stderr=fh)
    elif getPlatform() == PLATFORM_WINDOWS:
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
    else:
        raise NotImplementedError("Process spawning not implemented for your OS.")

def _getStartCommand(logger):
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
        return [_getPythonInterpreter(), os.path.join(get_settings().get_main_package_path(), "start_lunchinator.py")]
    else:
        logger.error("Restart not yet implemented for your OS.")
            
    return None
    
def _getPythonInterpreter():
    # sys.executable does not always return the python interpreter
    if getPlatform() == PLATFORM_WINDOWS: 
        if isPyinstallerBuild():
            raise Exception("There is no python interpreter in pyinstaller packages.")
        else:
            return sys.executable
    return which("python")

def stopWithCommands(args, logger):
    """
    Stops Lunchinator and execute commands
    """
    from lunchinator import get_server
    try:        
        spawnProcess(args, logger)
    except:
        logger.exception("Error in stopWithCommands")
        return
    if get_server().getController() != None:
        get_server().getController().shutdown()
            
def restartWithCommands(commands, logger):
    """
    Restart Lunchinator and execute commands in background while it is stopped.
    commands: lunchinator.commands.Commands instance
    """
    from lunchinator import get_server
    try:
        # copy restart script to safe place
        shutil.copy(get_settings().get_resource("bin", "restart.py"), get_settings().get_main_config_dir())
        
        startCmd = _getStartCommand(logger)
        args = [_getPythonInterpreter(), get_settings().get_config("restart.py"),
                "--lunchinator-path", get_settings().get_main_package_path(),
                "--start-cmd", json.dumps(startCmd),
                "--pid", str(os.getpid())]
        if commands != None:
            args.extend(["--commands", commands.toString()])
        
        spawnProcess(args, logger)
    except:
        logger.exception("Error in restartWithCommands")
        return
    if get_server().getController() != None:
        get_server().getController().shutdown()
    else:
        sys.exit(0)
    
def restart(logger):
    """Restarts the Lunchinator"""
    try:
        #on Windows with pyinstaller we use this special handling for now
        if getPlatform()==PLATFORM_WINDOWS:  
            frozen = getattr(sys, 'frozen', '')
            if frozen:
                logger.debug("Trying to spawn %s", sys.executable)
                from lunchinator import get_server
                get_server().stop_server()
                subprocess.Popen(sys.executable, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
                
        restartWithCommands(None, logger)
    except:
        logger.exception("Error restarting")

def formatTime(mTime):
    """Returns a human readable time representation given a struct_time"""
    dt = datetime.fromtimestamp(mktime(mTime))
    if dt.date() == datetime.today().date():
        return strftime("Today %H:%M", mTime)
    elif dt.date() == (datetime.today() - timedelta(days=1)).date():
        return strftime("Yesterday %H:%M", mTime)
    elif dt.date().year == datetime.today().date().year:
        return strftime("%b %d, %H:%M", mTime)
    return strftime("%b %d %Y, %H:%M", mTime)

def revealFile(path, logger):
    if not os.path.exists(path):
        logger.error("Trying to reveal file %s which does not exist.", path)
        return
    try:
        if getPlatform() == PLATFORM_MAC:
            from AppKit import NSWorkspace
            ws = NSWorkspace.sharedWorkspace()
            ws.selectFile_inFileViewerRootedAtPath_(path, os.path.dirname(path))
        elif getPlatform() == PLATFORM_WINDOWS:
            subprocess.call(['explorer', '/select', path])
        elif getPlatform() == PLATFORM_LINUX:
            subprocess.call(['xdg-open', os.path.dirname(path)])
    except:
        logger.exception("Could not reveal file")
        
def openFile(path, logger):
    if not os.path.exists(path):
        logger.error("Trying to open file %s which does not exist.", path)
        return
    try:
        if getPlatform() == PLATFORM_MAC:
            from AppKit import NSWorkspace
            ws = NSWorkspace.sharedWorkspace()
            ws.openFile_(path)
        elif getPlatform() == PLATFORM_WINDOWS:
            os.startfile(path)
        elif getPlatform() == PLATFORM_LINUX:
            subprocess.call(['xdg-open', path])
    except:
        logger.exception("Could not open file")
    
def formatException(exc_info=None):
    if exc_info is None:
        exc_info = sys.exc_info()
    typeName = u"Unknown Exception"
    if exc_info[0] != None:
        typeName = unicode(exc_info[0].__name__)
    return u"%s: %s" % (typeName, unicode(exc_info[1]))

def formatSize(num):
    num = float(num)
    if num < 1024 and num > -1024:
        return u"%3.0f\u2009%s" % (num, u"bytes")
    num /= 1024.0
    for x in [u'KiB', u'MiB', u'GiB']:
        if num < 1024.0 and num > -1024.0:
            return u"%3.1f\u2009%s" % (num, x)
        num /= 1024.0
    return u"%3.1f\u2009%s" % (num, u'TB')

def getUniquePath(defaultPath):
    if not os.path.exists(defaultPath):
        return defaultPath
    
    # have to make it unique
    name, ext = os.path.splitext(defaultPath)
    for i in itertools.count(2):
        newPath = "%s %d%s" % (name, i, ext)
        if not os.path.exists(newPath):
            return newPath

_validFilenameChars = None
def sanitizeForFilename(s):
    global _validFilenameChars
    if _validFilenameChars is None:
        _validFilenameChars = set("-_.() %s%s" % (string.ascii_letters, string.digits))
    return ''.join(c for c in s if c in _validFilenameChars)

REASON_PACKAGE_MISSING = 0
REASON_VERSION_CONFLICT = 1
REASON_UNKNOWN = 2

def checkRequirements(reqs, component, dispName, missing={}):
    """Checks Python environment for installed dependencies.
    
    Returns a dictionary {component name : (displayed name, requirement, reason, info)}
    for each requirement that is not met by the current environment.
    
    reqs -- List of requirement strings
    component -- Name of the component that requires the package
    dispName -- Displayed name of the component
    missing -- dictionary to update
    """
    
    for req in reqs:
        req = req.strip()
        try:
            get_distribution(req)
        except ResolutionError as e:
            if type(e) is DistributionNotFound:
                reason = REASON_PACKAGE_MISSING
                info = None
            elif type(e) is VersionConflict:
                reason = REASON_VERSION_CONFLICT
                info = e.args[0]
            else:
                reason = REASON_UNKNOWN
                info = None
            if component not in missing:
                missing[component] = []
            missing[component].append((dispName, req, reason, info))
    return missing
    
INSTALL_SUCCESS = 0
INSTALL_FAIL = 1
INSTALL_RESTART = 2
INSTALL_CANCELED = 3
INSTALL_NONE = 4
       
def installDependencies(requirements):
    if not requirements:
        getCoreLogger().info("No dependencies to install.")
        return INSTALL_SUCCESS
    
    if getPlatform()==PLATFORM_WINDOWS:
        result = installPipDependencyWindows(requirements)
    else:
        result = subprocess.call([get_settings().get_resource('bin', 'install-dependencies.sh')] + requirements)
    
    from lunchinator.lunch_server import EXIT_CODE_UPDATE
    if result == EXIT_CODE_UPDATE:
        # need to restart
        restart(getCoreLogger())
        return INSTALL_RESTART
    
    for req in requirements:
        try:
            get_distribution(req)
        except:
            return INSTALL_FAIL
    return INSTALL_SUCCESS
 
def handleMissingDependencies(missing, gui, optionalCallback=lambda _req : True):
    """If there are missing dependencies, asks and installs them.
    
    Returns a list of components whose requirements were not fully
    installed.
    
    missing -- dictionary returned by checkRequirements(...)
    optionalCallbacl -- function that takes a requirement string and returns
                        True if the requirement is optional and False
                        otherwise.
    """
    if missing:
        if isPyinstallerBuild():
            getCoreLogger().warning("There are missing dependencies in your PyInstaller build. " + \
            "Contact the developers.\n%s",str(missing))
            return INSTALL_NONE
        
        if gui:
            from lunchinator.req_error_dialog import RequirementsErrorDialog
            requirements = []
            for _component, missingList in missing.iteritems():
                for dispName, req, reason, info in missingList:
                    if reason == REASON_PACKAGE_MISSING:
                        reasonStr = u"Not installed"
                    elif reason == REASON_VERSION_CONFLICT:
                        reasonStr = u"Wrong version (installed: %s)" % info.version
                    else:
                        reasonStr = u"Unknown"
                    requirements.append((req,
                                         dispName,
                                         reasonStr,
                                         optionalCallback(req)))
            f = RequirementsErrorDialog(requirements, None)
            res = f.exec_()
            if res == RequirementsErrorDialog.Accepted:
                return installDependencies(f.getSelectedRequirements())
            else:
                return INSTALL_CANCELED
        return INSTALL_FAIL
    return INSTALL_NONE


    
def installPipDependencyWindows(package):
    """ installs dependecies for lunchinator working without pyinstaller on Win 
    """
    from lunchinator.lunch_server import EXIT_CODE_UPDATE, EXIT_CODE_ERROR
    import types
    
    getCoreLogger().debug("Trying to install %s", package)
    
    python_exe = sys.executable
    
    if type(package)==types.ListType:
        packageStr = " ".join(package)
    else:
        packageStr = package

    params = '-m pip install %s' % (packageStr)
        
    try:
        import win32api, win32con, win32event, win32process
        from win32com.shell.shell import ShellExecuteEx
        from win32com.shell import shellcon
    except:
        getCoreLogger().error("You need pywin32 to install dependencies automatically. " + \
        "You can try to install dependencies by running this as Administrator:\n" + \
        "%s %s", python_exe, params)        
        return EXIT_CODE_ERROR
    
    try:    
        procInfo = ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL,
                                  fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                                  lpDirectory="C:",
                                  lpVerb='runas',
                                  lpFile='"%s"'%python_exe,
                                  lpParameters=params)
    
        procHandle = procInfo['hProcess']    
        _obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
        rc = win32process.GetExitCodeProcess(procHandle)
        getCoreLogger().debug("DependencyInstall: Process handle %s returned code %s", procHandle, rc)
        return EXIT_CODE_UPDATE
    except:
        getCoreLogger().exception("Installation with pip failed")
        return EXIT_CODE_ERROR
        
    
