#!/usr/bin/python
#
#this script is used to start the lunchinator in all its flavors

if __name__ == '__main__':    
    try:        
        from lunchinator.start_lunchinator import startLunchinator
        startLunchinator()
    except Exception as e:
        import traceback
        traceback.print_exc()
        msg = "Unhandled Exception: "+str(e)
        try:
            from PyQt4.QtGui import QApplication, QMessageBox
            app = QApplication([])
            QMessageBox.critical(None, "Lunchinator Critical Error", msg)
        except:
            pass
