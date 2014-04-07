# -*- mode: python -*-
a = Analysis(['..\\\\start_lunchinator.py', '..\\\\plugins\\\\members_table\\\\__init__.py', 
			'..\\\\plugins\\\\remote_pictures\\\\__init__.py', 
			'..\\\\plugins\\\\online_update\\\\__init__.py', 
			'..\\\\plugins\\\\remote_pictures\\\\remote_pictures_gui.py',
			'..\\\\lunchinator\\\\lunch_button.py', 
			'..\\\\lunchinator\\\\shell_thread.py', 
			'..\\\\plugins\\\\simple_view\\\\simpleViewWidget.py'],
             pathex=['.'],
             hiddenimports=['SimpleHTTPServer', 'sqlite3', 'dbapi2', 'cgi', 'csv', 'Queue', 'netrc'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='lunchinator.exe',
          debug=False,
          strip=None,
          upx=False,
          console=False , icon='..\\images\\lunch.ico')
