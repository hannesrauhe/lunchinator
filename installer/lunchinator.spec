# -*- mode: python -*-
a = Analysis(['..\\\\start_lunchinator.py', '..\\\\plugins\\\\members_table\\\\__init__.py', '..\\\\plugins\\\\remote_pictures\\\\__init__.py', '..\\\\plugins\\\\remote_pictures\\\\remote_pictures_gui.py'],
             pathex=['C:\\Users\\d054203\\lunchinator\\installer'],
             hiddenimports=['urllib2', 'bisect', 'SimpleHTTPServer', 'sqlite3', 'dbapi2', 'cgi', 'csv', 'Queue', 'netrc'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='lunchinator.exe',
          debug=False,
          strip=None,
          upx=False,
          console=False , icon='..\\images\\lunch.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=False,
               name='lunchinator')
