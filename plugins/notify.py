from lunchinator.plugin import iface_called_plugin
from lunchinator import get_settings, get_peers
from lunchinator.utilities import displayNotification, getPlatform,\
    PLATFORM_LINUX, PLATFORM_MAC, PLATFORM_WINDOWS, which
import os, threading, subprocess, ctypes

class AttentionThread(threading.Thread):
    def __init__(self, audioFile, openTray, logger):
        super(AttentionThread, self).__init__()
        self._audioFile = audioFile
        self._openTray = openTray
        self.logger = logger
    
    def run(self):        
        myPlatform = getPlatform()
        if myPlatform == PLATFORM_LINUX:
            self._drawAttentionLinux(self._audioFile, self._openTray)
        elif myPlatform == PLATFORM_MAC:
            self._drawAttentionMac(self._audioFile, self._openTray)
        elif myPlatform == PLATFORM_WINDOWS:
            self._drawAttentionWindows(self._audioFile, self._openTray)
            
    def _call(self, call, desc):
        try:
            subprocess.call(call)
        except:
            self.logger.exception("notify error (%s): Error calling %s", desc, ' '.join(call))
            
    def _drawAttentionLinux(self, audioFile, openTray):
        if openTray:
            self._call(["eject", "-T", "/dev/cdrom"], "eject")
        
        playExe = which("paplay")
        if playExe:
            self._call([playExe, audioFile], "play sound")
        else:
            # try SoX
            playExe = which("play")
            if playExe:
                self._call([playExe, "-q", audioFile], "play sound")
            else:
                self.logger.error("No audio player found, cannot play sound.")
    
        if openTray:
            self._call(["eject", "-T", "/dev/cdrom"], "close")
            
    def _drawAttentionMac(self, audioFile, openTray):
        if openTray:
            self._call(["drutil", "tray", "eject"], "eject")      
    
        self._call(["afplay", audioFile], "play sound")         
             
        if openTray:
            self._call(["drutil", "tray", "close"], "close")
    
    def _drawAttentionWindows(self, audioFile, openTray):
        if openTray:
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                self.logger.exception("notify error: eject error (open)")
        
        try:
            from PyQt4.QtGui import QSound
            q = QSound(audioFile)
            q.play()
        except:        
            self.logger.exception("notify error: sound")
        
        if openTray:    
            try:
                ctypes.windll.WINMM.mciSendStringW(u"set cdaudio door open", None, 0, None)
            except:
                self.logger.exception("notify error: eject error (close)")
        
class Notify(iface_called_plugin):    
    def __init__(self):
        super(Notify, self).__init__()
        self.options = [((u"icon_file", u"Icon if no avatar"),get_settings().get_resource("images", "mini_breakfast.png")),
                        ((u"audio_file", u"Audio File for Lunch Messages",self.audioFileChanged), get_settings().get_resource("sounds", "sonar.wav")),
                        ((u"open_optival_drive", "Open Optical Drive on Lunch"), True)]
        self.force_activation = True
        self.attentionThread = None
        
    def audioFileChanged(self,_setting,new_value):
        audio_file=self.options[u"audio_file"]
        if os.path.exists(new_value):
            audio_file = new_value
        elif os.path.exists(get_settings().get_main_config_dir()+"/sounds/"+new_value):
            audio_file= get_settings().get_main_config_dir()+"/sounds/"+new_value
        else:
            try:
                # get_resource will raise if the resource does not exist.
                audio_file = get_settings().get_resource("sounds", new_value)
            except:
                self.logger.error("configured audio file %s does not exist in sounds folder, using old one", new_value)
            # don't set the new value, keep old value
        return audio_file
    
    def drawAttention(self, audioFile, openTray):
        if self.attentionThread is not None and self.attentionThread.isAlive():
            # someone is already drawing attention at the moment
            self.logger.debug("Drawing attention is already in progress.")
            return
        else:
            self.logger.debug("Starting new attention thread.")
            self.attentionThread = AttentionThread(audioFile, openTray, self.logger)
            self.attentionThread.start()
    
    def process_message(self, msg, ip, _member_info):
        name = u"[%s]" % get_peers().getDisplayedPeerName(pIP=ip)
        icon = get_peers().getPeerAvatarFile(pIP=ip)
        if not icon:
            icon = self.options[u"icon_file"]
        
        displayNotification(name, msg, self.logger, icon)
            
    def process_lunch_call(self,_msg,_ip,_member_info):
        self.drawAttention(self.options[u"audio_file"], self.options[u"open_optival_drive"])

    def process_event(self,cmd,value,ip,member_info,_prep):
        pass
