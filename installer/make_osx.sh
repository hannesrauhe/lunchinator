git rev-list HEAD --count > ../version

# ensure pyinstaller is in PATH

pyinstaller -y -F -w lunchinator_osx.spec

cat > dist/Lunchinator.app/Contents/Resources/qt.conf <<EOF
[paths]
Plugins=MacOS/qt4_plugins
EOF

cp -r ../bin ../images ../lunchinator ../plugins ../sounds ../yapsy ../start_lunchinator.py  dist/Lunchinator.app/Contents
cp $(which terminal-notifier) dist/Lunchinator.app/Contents

