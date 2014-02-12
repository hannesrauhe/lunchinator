# -*- mode: python -*-
a = Analysis(['../start_lunchinator.py', '../plugins/members_table/__init__.py', '../plugins/remote_pictures/__init__.py', '../plugins/remote_pictures/remote_pictures_gui.py'],
             pathex=['C:\\Users\\d054203\\lunchinator\\installer'],
             hiddenimports=['urllib2', 'bisect', 'SimpleHTTPServer', 'sqlite3', 'dbapi2', 'cgi', 'csv', 'Queue', 'netrc'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Lunchinator',
          debug=False,
          strip=None,
          upx=True,
          console=False , icon='../images/lunch.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='Lunchinator')
app = BUNDLE(coll,
             name='Lunchinator.app',
             info_plist={
               'NSPrincipalClass': 'NSApplication',
               'LSUIElement': 'True'
             },
             icon='../images/lunch.icns')
