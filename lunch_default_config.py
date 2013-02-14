import sys,os

class lunch_default_config(object):
    audio_file ="sonar.wav"
    user_name = ""
    debug = False
    auto_update = True    
    main_config_dir = os.getenv("HOME")+"/.lunchinator"
    members_file = main_config_dir+"/lunch_members.cfg"
    peer_timeout = 604800 #one week so that we don't forget someone too soon
    mute_timeout = 30
    config_dirs = [sys.path[0],main_config_dir]
    icon_file = sys.path[0]+"/images/mini_breakfast.png"