#!/usr/bin/python
#
# this script issues git pull and starts the lunchinator
# the lunchinator must be closed before running

import sys, subprocess, os, platform, logging

pythonex_wo_console = "/usr/bin/python"
pythonex_w_console = "/usr/bin/python"

if platform.system()=="Windows":
    pythonex_w_console = "python"
    pythonex_wo_console = "pythonw"
    
def runGitCommand(args, path):     
    call = ["git","--no-pager","--git-dir="+path+"/.git","--work-tree="+path]
    call = call + args
     
    fh = subprocess.PIPE
    p = subprocess.Popen(call,stdout=fh, stderr=fh)
    pOut, pErr = p.communicate()
    retCode = p.returncode
    return retCode, pOut, pErr

if __name__ == "__main__":
    console_output = False
    if len(sys.argv)>1:
        lunchbindir = sys.argv[1]
        if len(sys.argv)>2 and sys.argv[2]=="--console-output":
            console_output = True
    else:
        print "usage: %s <lunchinator-path> [--console-output]"%sys.argv[0]
        sys.exit(1)
        
    if not console_output:
        logfilepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'update_lunchinator.log')
        logging.basicConfig(filename=logfilepath,level=logging.DEBUG)
    
    c, o, e = runGitCommand(["pull"],lunchbindir)
    if c==0:
        logging.debug(o)
        logging.debug("Lunchinator successfully updated")
    else:
        logging.error("There was an error while executing the git command:")
        logging.error(e)
        
    if console_output:
        raw_input("Press Enter to restart the lunchinator...")
    else:
        print "A log of the Update can be found here: "+logging.getLogger().handlers[0].baseFilename
    
    args = [pythonex_wo_console, os.path.join(lunchbindir,"start_lunchinator.py")]
    if platform.system()=="Windows":
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
    else:
        subprocess.Popen(" ".join(args), shell=True, close_fds=True)

