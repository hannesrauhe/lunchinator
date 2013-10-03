#!/usr/bin/python
import hashlib, shutil
import os
import Image
from lunchinator import log_exception, log_error, get_settings

class l_avatar(object):
    size = 128, 128
         
    def md5_for_file(self,file_path, block_size=2**20):
        with open(file_path,'rb') as f:
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
                log_exception("cannot create thumbnail for '%s'" % infile)
                raise
    
    def use_as_avatar(self,file_path):    
        if not os.path.exists(file_path):
            log_error("no image found at",file_path,", exiting")
            raise
        self.scale_image(file_path,get_settings().get_avatar_dir()+"/tmp.jpg")
        avatar_name = unicode(self.md5_for_file(file_path)+".jpg")
        shutil.copy(get_settings().get_avatar_dir()+"/tmp.jpg",get_settings().get_avatar_dir()+"/"+avatar_name)
        
        get_settings().set_avatar_file(avatar_name, True)
        return get_settings().get_avatar_dir()+"/"+avatar_name