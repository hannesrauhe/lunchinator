#!/bin/bash

if [ "$OBSUSERNAME" == "" ]
then
  echo "Please export OBSUSERNAME to your environment."
  exit -1
fi

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
        pushd osc/home:${OBSUSERNAME}/lunchinator &>/dev/null
        for f in $(osc st | grep '^?' | sed -e 's/^?\s*//')
        do
          echo "Deleting ${f}"
          rm "$f"
        done
        popd &>/dev/null
        exit 0
        ;;
    -h)
        echo "Use with -p|--publish to publish to Launchpad immediately."
        exit 0
        ;;
  esac

  shift
done

if ! type osc &>/dev/null
then
  echo "Please install osc first."
  exit 1
fi

if ! type rpm &>/dev/null
then
  echo "Please install rpm first."
  exit 1
fi

mkdir -p osc
if [ ! -d osc/home:${OBSUSERNAME} ]
then
  echo "Checking out repository..."
  pushd osc
  osc checkout home:${OBSUSERNAME}
  popd
fi

source determine_version.sh

# version has to be located besides setup.py
echo $VERSION > ../version

export dist=
# if this is run on Ubuntu, have setup.py know this is not for Ubuntu.
export __notubuntu=1
pushd ..
python setup.py sdist --dist-dir=installer/osc/home:${OBSUSERNAME}/lunchinator
python setup.py bdist_rpm --spec-only --dist-dir=installer/osc/home:${OBSUSERNAME}/lunchinator
popd
sed -i -e 's/\(^BuildArch.*$\)/#\1/' osc/home:${OBSUSERNAME}/lunchinator/Lunchinator.spec
#sed -i -e 's/\(python setup\.py install.*$\)/\1 --prefix=usr --exec-prefix=usr/' osc/home:${OBSUSERNAME}/lunchinator/Lunchinator.spec
#sed -i -e '/%files.*/r add_files' osc/home:${OBSUSERNAME}/lunchinator/Lunchinator.spec
if $PUBLISH
then
  pushd osc/home:${OBSUSERNAME}/lunchinator
  osc add Lunchinator.spec
  for f in $(osc st | grep '^?' | sed -e 's/^?\s*//')
  do
    osc add "$f"
  done
  osc commit
  popd
fi
