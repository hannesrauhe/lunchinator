#!/usr/bin/python
from lunch_default_config import *
import socket,sys,os,hashlib,shutil
import os, sys
import Image

class l_avatar(object):
    size = 128, 128
         
    def md5_for_file(self,file_path, block_size=2**20):
        f = open(file_path,'rb')
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()
        
    def scale_image(self,infile,outfile):
        if infile != outfile:
            try:
                im = Image.open(infile)
                im.thumbnail(self.size, Image.ANTIALIAS)
                im.save(outfile, "JPEG")
            except IOError:
                print "cannot create thumbnail for '%s'" % infile
                raise
    
    def use_as_avatar(self,config_ob,file_path):    
        if not os.path.exists(file_path):
            print "no image found at",file_path,", exiting"
            raise
        self.scale_image(file_path,config_ob.get_avatar_dir()+"/tmp.jpg")
        avatar_name = self.md5_for_file(file_path)+".jpg"
        shutil.copy(config_ob.get_avatar_dir()+"/tmp.jpg",config_ob.avatar_dir+"/"+avatar_name)
        
        config_ob.set_avatar_file(avatar_name, True)
        return config_ob.avatar_dir+"/"+avatar_name
    
if __name__ == "__main__":    
    lpic = l_avatar()
    
    file_path = lpic.main_config_dir+"/userpic.jpg"
    if len(sys.argv)>1:
        file_path =sys.argv[1]
    
    lpic.use_as_avatar(file_path)