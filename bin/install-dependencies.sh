#!/bin/bash

if [ $(uname) == "Darwin" ]
then
  if type pip-2.7 &>/dev/null
  then
    PIP=pip-2.7
  elif type pip-2.6 &>/dev/null
  then
    PIP=pip-2.6
  elif type pip &>/dev/null
  then
    PIP=pip
  fi
  
  # ensure pip does not install into current package
  pushd "$HOME"  
  INSTALL="${PIP} install $@"
  osascript -e "do shell script \"${INSTALL}\" with administrator privileges"
  popd
  exit $?
elif [ $(uname) == "Linux" ]
then
  if type gksu &>/dev/null
  then
    SUDO=gksu
  elif type gnomesu &>/dev/null
  then
    SUDO=gnomesu
  fi
      
  # ensure pip does not install into current package
  pushd "$HOME"
  $SUDO "pip install $@"
  popd
  exit $?
else
  # unknown OS
	exit 1
fi
