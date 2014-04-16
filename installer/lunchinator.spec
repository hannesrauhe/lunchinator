# -*- mode: python -*-
a = Analysis(['lunchinator.specgit', 'pul'],
             pathex=['C:\\Users\\d054203\\lunchinator\\installer'],
             hiddenimports=[],
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
          upx=True,
          console=True )
