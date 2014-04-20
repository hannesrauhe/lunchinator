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
  if ! type pip &>/dev/null || ! $SUDO pip install $@
  then
    # error or pip not available. check if at least, yapsy was installed
    if ! python -c 'import yapsy' &>/dev/null
    then
      # yapsy is not installed - try again with easy_install
      echo "Installation with pip failed, trying again with easy_install"
      $SUDO easy_install $@
      EXITST=$?
    else
      # yapsy was installed. exit with 1 anyways to indicate error. 
      EXITST=1
    fi
  else
    # no errors
    EXITST=0
  fi
  popd
  exit $EXITST
else
  # unknown OS
	exit 1
fi
