#!/bin/bash
pushd ..
rm -rf deb_dist
python setup.py --command-packages=stdeb.command sdist_dsc
cd deb_dist/lunchinator-*
echo "gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light" >>debian/*.postinst
echo "gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark" >>debian/*.postinst
dpkg-buildpackage -rfakeroot -uc -us
popd
exit 0

# old version
rm -rf dist

echo "*** Compiling Application ***"
pyinstaller -y -F -w lunchinator_lin.spec
git rev-list HEAD --count > dist/lunchinator/version

echo "*** copying python code ***"
cp -r ../bin ../images ../lunchinator ../plugins ../sounds ../yapsy ../start_lunchinator.py  dist/lunchinator

echo "*** Creating Package Structure ***"
mkdir -p dist/DEBIAN
mkdir -p dist/usr/bin
mkdir -p dist/usr/lib
mkdir -p dist/usr/share/applications
mkdir -p dist/usr/share/icons/hicolor/scalable/apps
mkdir -p dist/usr/share/icons/ubuntu-mono-dark/status/24/
mkdir -p dist/usr/share/icons/ubuntu-mono-light/status/24/

cat > dist/DEBIAN/postinst <<EOF
gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light
gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark
EOF
chmod 755 dist/DEBIAN/postinst

cat > dist/usr/share/applications/lunchinator.desktop <<EOF
[Desktop Entry]
Type=Application
Encoding=UTF-8
Name=lunchinator
GenericName=The Lunchinator
Comment=It's the Lunchinator.
Exec=lunchinator
Icon=lunch
Terminal=false
Categories=Utilities;Application
EOF

cat > dist/usr/bin/lunchinator <<EOF
#!/bin/bash
pushd /usr/lib/lunchinator
./lunchinator_exe
popd
EOF

chmod +x dist/usr/bin/lunchinator

mv dist/lunchinator dist/usr/lib/

# install icons for mono-dark (yes, the 'light' icon is for the dark theme)
cp ../images/lunchlight.svg dist/usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg
cp ../images/lunchred.svg dist/usr/share/icons/ubuntu-mono-dark/status/24/lunchinatorred.svg

# install icons for mono-light
cp ../images/lunch.svg dist/usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg
cp ../images/lunchred.svg dist/usr/share/icons/ubuntu-mono-light/status/24/lunchinatorred.svg

# install program icon
cp ../images/lunch.svg dist/usr/share/icons/hicolor/scalable/apps

cat > dist/DEBIAN/control <<EOF
Package: lunchinator
Version: $(git rev-list HEAD --count)
Section: Application/Utilities
Priority: optional
Architecture: amd64
Depends:
Maintainer: Cornelius Ratsch <ratsch@stud.uni-heidelberg.de>
Installed-Size: $(du -s dist/usr/ | cut -f 1 -d $'\t') 
Description: The Lunchinator.
 It's the Lunchinator. It does lunch stuff.
EOF

echo "*** Creating Debian package ***"
fakeroot dpkg-deb --build dist
source /etc/lsb-release
DEB_NAME=lunchinator_$(git rev-list HEAD --count)_${DISTRIB_RELEASE}.deb
mv dist.deb dist/"$DEB_NAME" 

echo "*** Creating signature file ***"
python hashNsign.py dist/"$DEB_NAME"
