for /f "tokens=*" %%a in ('git describe --tags --abbrev^=0') do set tagname=%varText%%%a
for /f "tokens=*" %%a in ('git rev-list HEAD --count') do set commitcount=%varText%%%a
echo %tagname%.%commitcount% > ..\\version

C:\\Python27\\scripts\\pyinstaller.exe -y -F -w lunchinator.spec

"C:\\Program Files (x86)\\Inno Setup 5\\Compil32.exe" /cc build_installer.iss

"C:\\Python27\\python.exe" hashNsign.py win/setup_lunchinator.exe