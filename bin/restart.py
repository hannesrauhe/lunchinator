import errno, time, os, json, platform, subprocess, sys
from optparse import OptionParser

def parse_args():
    usage = "usage: %prog [options]"
    optionParser = OptionParser(usage=usage)
    optionParser.add_option("-l", "--lunchinator-path", default=None, dest="lunchinatorPath",
                      help="Path to the Lunchinator main package (main_package_path).")
    optionParser.add_option("-c", "--commands", default=None, dest="commands",
                      help="Commands to execute before exiting (JSON list of argument lists).")
    optionParser.add_option("-s", "--start-cmd", default=None, dest="startCmd",
                      help="Command to execute to start Lunchinator (JSON list of arguments).")
    optionParser.add_option("-p", "--pid", default=None, dest="pid",
                      help="Process ID of old Lunchinator instance.")
    return optionParser.parse_args()

def isRunning(pid):
    if platform.system()=="Windows":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x100000
    
        process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
        if process != 0:
            kernel32.CloseHandle(process)
            return True
        else:
            return False
        
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            return False
    return True

def executeCommand(args):
    from lunchinator.utilities import spawnProcess
    spawnProcess(args, getCoreLogger())

def restart():
    # wait for Lunchinator to exit
    try:
        pid = int(options.pid)
        getCoreLogger().info("Waiting for Lunchinator (pid %s) to terminate", options.pid)
        c = 0
        while isRunning(pid) and c<100:
            time.sleep(1. / 5)
            c+=1
            if 0==c%10:
                getCoreLogger().info("Lunchinator (pid %s) still running", options.pid)
            
        if isRunning(pid):            
            getCoreLogger().info("Lunchinator (pid %s) still running, aborting restart", options.pid)
            sys.exit(1)
            
    except ValueError:
        getCoreLogger().error("Invalid pid: %d", options.pid)
    
    getCoreLogger().info("Lunchinator gone")
    # execute commands while Lunchinator is not running
    cmdString = options.commands
    if cmdString:
        getCoreLogger().info("Executing commands while Lunchinator is not running...")
        commands = Commands(getCoreLogger(), cmdString)
        commands.executeCommands()

    # restart Lunchinator
    startCmd = options.startCmd
    if startCmd:
        args = json.loads(startCmd)
        getCoreLogger().info("Restarting Lunchinator: %s", ' '.join(args))
        
        if platform.system()=="Windows":
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
        else:
            subprocess.call(args, close_fds=True)

if __name__ == '__main__':
    (options, _args) = parse_args()
    
    lunchinatorPath = options.lunchinatorPath
    if lunchinatorPath:
        sys.path.insert(0, lunchinatorPath)
    
    from lunchinator import MAIN_CONFIG_DIR
    from lunchinator.log import initializeLogger, getCoreLogger
    initializeLogger(os.path.join(MAIN_CONFIG_DIR, "update.log"))
    
    try:
        from lunchinator.commands import Commands
        restart()
    except:
        getCoreLogger().exception("Unrecoverable error during restart.")
    
