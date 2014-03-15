git rev-list HEAD --count > ..\\version

C:\\Python27\\scripts\\pyinstaller.exe -y -F -w lunchinator.spec

"C:\\Program Files (x86)\\Inno Setup 5\\Compil32.exe" /cc build_installer.iss

"C:\\Python27\\python.exe" hashNsign.py windows/setup_lunchinator.exe