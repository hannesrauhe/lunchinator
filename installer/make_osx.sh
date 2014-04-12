#!/bin/bash

# ensure pyinstaller is in PATH

rm -rf build/ dist/

echo "*** Building Application Bundle ***"
pyinstaller -y -F -w lunchinator_osx.spec

git rev-list HEAD --count > dist/Lunchinator.app/Contents/version
cat > dist/Lunchinator.app/Contents/Resources/qt.conf <<EOF
[paths]
Plugins=MacOS/qt4_plugins
EOF

echo "*** copying python code into bundle ***"
cp -r ../bin ../images ../lunchinator ../plugins ../sounds ../start_lunchinator.py  dist/Lunchinator.app/Contents
cp $(which terminal-notifier) dist/Lunchinator.app/Contents
mkdir dist/Lunchinator.app/Contents/gnupg
cp $(which gpg) dist/Lunchinator.app/Contents/gnupg

echo "*** Creating tarball ***"
cd dist
tar cjf Lunchinator.app.tbz Lunchinator.app
cd ..

echo "*** Creating signature file ***"
python hashNsign.py dist/Lunchinator.app.tbz
