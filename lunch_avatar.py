#!/usr/bin/python
from lunch_default_config import *
import socket,sys,os,hashlib,shutil

class lunch_avatar(lunch_default_config):     
    def md5_for_file(self,file_path, block_size=2**20):
        f = open(file_path,'rb')
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()
    
    def use_as_avatar(self,file_path):    
        if not os.path.exists(file_path):
            print "no image found at",file_path,", exiting"
            raise
        file_name, file_ext = os.path.splitext(file_path)    
        avatar_name = self.md5_for_file(file_path)+file_ext
        shutil.copy(file_path,self.avatar_dir+"/"+avatar_name )
        
        
        f = open(self.main_config_dir+"/avatar.cfg",'w')
        f.truncate()
        f.write(avatar_name)
        f.close();
    
if __name__ == "__main__":
    lpic = lunch_avatar()
    if len(sys.argv)>1:
        file_path = sys.argv[1]
    else:
        file_path = lpic.main_config_dir+"/userpic.jpg"
        
    print lpic.use_as_avatar(file_path)