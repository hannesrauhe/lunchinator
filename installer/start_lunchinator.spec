# -*- mode: python -*-
a = Analysis(['..\\start_lunchinator.py', '..\\lunchinator\\__init__.py', '..\\plugins\\lunch_button.py', '..\\lunchinator\\lunch_button.py'],
             pathex=['C:\\Users\\d054203\\lunchinator\\installer'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='start_lunchinator.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='start_lunchinator')
