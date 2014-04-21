#!/bin/bash

args=$(getopt -l "publish,clean" -o "pc" -- "$@")

if [ ! $? == 0 ]
then
  exit 1
fi

eval set -- "$args"

PUBLISH=false

while [ $# -ge 1 ]; do
  case "$1" in
    --)
        # No more options left.
        shift
        break
       ;;
    -p|--publish)
        PUBLISH=true
        shift
        ;;
    -c|--clean)
        rm -rf build dist
        exit 0
        ;;
    -h)
        echo "Use with -p|--publish to publish to Launchpad immediately."
        exit 0
        ;;
  esac

  shift
done


# ensure pyinstaller is in PATH

source determine_version.sh
echo "$VERSION" > ../version

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

if $PUBLISH
then
  USER=$(security find-internet-password -s update.lunchinator.de | grep "acct" | cut -d '"' -f 4)
  PASSWD=$(security 2>&1 >/dev/null find-internet-password -gs update.lunchinator.de | cut -d '"' -f 2)
  ncftp <<EOF
open -u ${USER} -p ${PASSWD} ftp://update.lunchinator.de/mac/
mput -rf dist/${VERSION}/
mput -f dist/latest_version.asc
quit
EOF
fi
