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

# -*- mode: python -*-
a = Analysis(anaFiles,
             pathex=['.'],
             hiddenimports=['netrc'],
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
		  console = False,
		  icon='..\\images\\lunchinator.ico')
		  
