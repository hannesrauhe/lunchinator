C:\\Python27\\scripts\\pyinstaller.exe -y -F -w ^
-n lunchinator ^
--noupx ^
--icon=..\\images\\lunch.ico ^
--hidden-import=urllib2 ^
--hidden-import=bisect ^
--hidden-import=SimpleHTTPServer ^
--hidden-import=sqlite3 ^
--hidden-import=dbapi2 ^
--hidden-import=cgi ^
--hidden-import=csv ^
--hidden-import=Queue ^
--hidden-import=netrc ^
..\\start_lunchinator.py ^
..\\plugins\\members_table\\__init__.py ^
..\\plugins\\remote_pictures\\__init__.py ^
..\\plugins\\remote_pictures\\remote_pictures_gui.py

"C:\\Program Files (x86)\\Inno Setup 5\\Compil32.exe" /cc build_installer.iss

"C:\\Python27\\python.exe" hashNsign.py windows/setup_lunchinator.exe