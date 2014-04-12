#!/bin/bash

dists=(lucid precise saucy trusty)

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
        rm -rf deb_*/ *.log dist
        exit 0
        ;;
    -h)
        echo "Use with -p|--publish to publish to Launchpad immediately."
        exit 0
        ;;
  esac

  shift
done

if [ "$DEBFULLNAME" == "" ] || [ "$DEBEMAIL" == "" ]
then
  echo "Please export DEBFULLNAME and DEBEMAIL to your environment."
  exit -1
fi

# version has to be located besides setup.py
git rev-list HEAD --count > ../version

for dist in "${dists[@]}"
do
  echo -e "\e[00;31m***** Creating source package for ${dist} *****\e[00m"
  export dist
  rm -rf dist deb_${dist}
  pushd ..
  python setup.py sdist --dist-dir=installer/dist
  popd
  py2dsc --suite=${dist} --dist-dir=deb_${dist} dist/Lunchinator*
  pushd deb_${dist}/lunchinator-*
  echo "gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light" >>debian/*.postinst
  echo "gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark" >>debian/*.postinst
  debuild -S 2>&1 | tee ../../${dist}.log
  if $PUBLISH
  then
    pushd ..
    echo -e "\e[00;31m***** Publishing package for ${dist} *****\e[00m"
    dput ppa:lunch-team/lunchinator lunchinator_*.changes
    popd
  fi
  popd
done
