# -*- mode: python -*-
a = Analysis(['../start_lunchinator.py',
              '../plugins/members_table/__init__.py',
              '../plugins/simple_view/__init__.py',
              '../plugins/remote_pictures/__init__.py',
              '../plugins/remote_pictures/remote_pictures_gui.py',
              '../plugins/online_update/__init__.py'],
             pathex=['.'],
             hiddenimports=['SimpleHTTPServer', 'sqlite3', 'dbapi2', 'cgi', 'csv', 'Queue', 'netrc'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='lunchinator_exe',
          debug=False,
          strip=True,
          upx=True,
          console=False , icon='../images/lunch.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=True,
               upx=True,
               name='lunchinator')
