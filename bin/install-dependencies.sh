#!/bin/bash

function vercomp () {
    if [[ $1 == $2 ]]
    then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 2
        fi
    done
    return 0
}

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
  
  vercomp $(pip --version | sed -e 's/\S*\s*\(\S*\).*/\1/') '1.4'
  if [ $? -le 1 ]
  then
    PIPRECENT=true
  else
    PIPRECENT=false
  fi
  
  $SUDO bash <<EOF
    if ! $PIPRECENT
    then
      easy_install --upgrade pip
    fi
    
	  if ! type pip &>/dev/null || ! $SUDO pip --proxy=$http_proxy install $@
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
  EOF
  popd
  exit $EXITST
else
  # unknown OS
	exit 1
fi
