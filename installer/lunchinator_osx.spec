# -*- mode: python -*-

import os
anaFiles = ["../start_lunchinator.py"]
anaFiles.extend(aFile for aFile in os.listdir("../plugins") if os.path.isfile(aFile) and aFile.endswith(".py"))
for aFile in os.listdir("../plugins"):
    aFile = os.path.join("../plugins", aFile)
    if aFile.endswith(".py"):
        anaFiles.append(aFile)
    if os.path.isdir(aFile):
        if os.path.exists(os.path.join(aFile, "__init__.py")):
            anaFiles.append(os.path.join(aFile, "__init__.py"))
        
a = Analysis(anaFiles,
             pathex=['..'],
             #hiddenimports=['cgi', 'netrc'],
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
          console=False , icon='../images/lunchinator.icns')
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
               'CFBundleIdentifier': "hannesrauhe.lunchinator",
               'NSPrincipalClass': 'NSApplication',
               'LSUIElement': 'True',
               'LSBackgroundOnly': 'False'
             },
             icon='../images/lunchinator.icns')
