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
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            return False
    return True

def executeCommand(args):
    from lunchinator.utilities import spawnProcess
    spawnProcess(args)

def restart():
    # wait for Lunchinator to exit
    try:
        pid = int(options.pid)
        log_info("Waiting for Lunchinator (pid %s) to terminate" % options.pid)
        while isRunning(pid):
            time.sleep(1. / 5)
    except ValueError:
        log_error("Invalid pid:", options.pid)
    
    # execute commands while Lunchinator is not running
    cmdString = options.commands
    if cmdString:
        log_info("Executing commands while Lunchinator is not running...")
        commands = Commands(cmdString)
        commands.executeCommands()

    # restart Lunchinator
    startCmd = options.startCmd
    if startCmd:
        args = json.loads(startCmd)
        log_info("Restarting Lunchinator:", ' '.join(args))
        
        if platform.system()=="Windows":
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
        else:
            subprocess.call(args, close_fds=True)

if __name__ == '__main__':
    (options, _args) = parse_args()
    
    lunchinatorPath = options.lunchinatorPath
    if lunchinatorPath:
        sys.path.insert(0, lunchinatorPath)
    
    from lunchinator import get_settings, log_exception, initialize_logger
    initialize_logger(get_settings().get_config("update.log"))
    
    try:
        from lunchinator import log_info, log_error
        from lunchinator.commands import Commands
        restart()
    except:
        log_exception("Unrecoverable error during restart.")
    
