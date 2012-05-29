#!/bin/bash

. /etc/*release

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

git pull

if grep -q $(hostname) lunch_members
	then echo "already a lunch member"
else
	echo $(hostname) >> lunch_members
 	git add lunch_members
	git commit -m "added $(hostname) automatically"
	git push
	python lunch_updater.py
fi

#execute right script depending on distribution here
echo ${DISTRIB_DESCRIPTION:0:6}

if [ "${DISTRIB_DESCRIPTION:0:6}" = "Ubuntu" ]; then
    unbuffer $DIR/indicator_applet.py >> $HOME/.lunch_calls
else
    unbuffer $DIR/gui_tray.py >> $HOME/.lunch_calls
fi
#

