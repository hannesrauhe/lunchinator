#!/usr/bin/python
import hashlib, shutil
import os
from lunchinator import get_settings
from PyQt4.QtGui import QImage, QPixmap
from PyQt4.QtCore import Qt

class l_avatar(object):
    width = 128
    height = 128
    
    def __init__(self, logger):
        self.logger = logger
         
    def md5_for_file(self, file_path, block_size=2 ** 20):
        with open(file_path, 'rb') as f:
            md5 = hashlib.md5()
            while True:
                data = f.read(block_size)
                if not data:
                    break
                md5.update(data)
            return md5.hexdigest()
        
    def scale_image(self, infile, outfile):
        if infile != outfile:
            try:
                qtimage = QImage(infile)
                pixmap = QPixmap.fromImage(qtimage)
                pixmap = pixmap.scaled(self.width, self.height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pixmap.save(outfile, "PNG")
            except IOError:
                self.logger.exception("cannot create thumbnail for '%s'", infile)
    
    def use_as_avatar(self, file_path):    
        if not os.path.exists(file_path):
            self.logger.error("no image found at %s, exiting", file_path)
            return

        tmpPath = os.path.join(get_settings().get_avatar_dir(), "tmp.png")
        self.scale_image(file_path, tmpPath)
        avatar_name = unicode(self.md5_for_file(file_path) + ".png")
        shutil.move(tmpPath, os.path.join(get_settings().get_avatar_dir(), avatar_name))
        
        get_settings().set_avatar_file(avatar_name)
        return os.path.join(get_settings().get_avatar_dir(), avatar_name)
