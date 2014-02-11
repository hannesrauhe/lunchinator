git rev-list HEAD --count > ../version

# ensure pyinstaller is in PATH

pyinstaller -y -F -w lunchinator_osx.spec
# don't search for Qt plugins or something (images don't work, but it does not crash)
touch dist/Lunchinator.app/Contents/Resources/qt.conf

