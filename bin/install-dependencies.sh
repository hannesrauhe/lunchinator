#!/bin/bash

export EXIT_RESTART=2

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
  
  EXITST=$($SUDO bash <<EOF
    if ! type pip &>/dev/null || ! pip install $@ 1>&2
    then
      # error or pip not available. check if at least, yapsy was installed
      if ! python -c 'import yapsy' &>/dev/null
      then
        # yapsy is not installed - try again with easy_install
        echo "Installation with pip failed, trying again with easy_install" 1>&2
        easy_install $@ 1>&2
        
        # check if easy_install installed at least yapsy
        if python -c 'import yapsy' &>/dev/null
        then
          # yapsy was installed, need to restart lunchinator
          echo $EXIT_RESTART
        else
          echo 1
        fi
      else
        # yapsy was installed. exit with 1 anyways to indicate error. 
        echo 1
      fi
    else
      # no errors
      echo 0
    fi
EOF)
  popd
  exit $EXITST
else
  # unknown OS
  exit 1
fi
