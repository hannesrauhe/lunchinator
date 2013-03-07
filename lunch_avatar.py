#!/usr/bin/python
from lunch_default_config import *
import socket,sys,os,hashlib,shutil
import os, sys

class lunch_avatar(lunch_default_config):
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
    
    def use_as_avatar(self,file_path):    
        if not os.path.exists(file_path):
            print "no image found at",file_path,", exiting"
            raise
        file_name, file_ext = os.path.splitext(file_path)    
        avatar_name = self.md5_for_file(file_path)+file_ext
        shutil.copy(file_path,self.avatar_dir+"/"+avatar_name )
        if self.debug:
            print "using",file_path,"as avatar - copied: ",avatar_name
        
        self.set_avatar_file(avatar_name, True)
        
    def scale_image(self,infile,outfile):
        if infile != outfile:
            try:
                import Image
                im = Image.open(infile)
                im.thumbnail(self.size, Image.ANTIALIAS)
                im.save(outfile, "JPEG")
            except IOError:
                print "cannot create thumbnail for '%s'" % infile
    
if __name__ == "__main__":    
    lpic = lunch_avatar()
    
    file_path = lpic.main_config_dir+"/userpic.jpg"
    if len(sys.argv)>1:
        infile = sys.argv[1]
        if os.path.exists(infile):
            lpic.scale_image(infile, file_path)
    
    lpic.use_as_avatar(file_path)