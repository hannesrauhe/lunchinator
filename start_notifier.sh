#!/bin/bash

. /etc/*release

LUNCHINATOR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LUNCHINATOR_CONFIG_DIR=$HOME/.lunchinator
cd $LUNCHINATOR_DIR
mkdir -p $LUNCHINATOR_CONFIG_DIR
mv *.cfg $LUNCHINATOR_CONFIG_DIR

git pull

#if grep -q $(hostname) lunch_members
#	then echo "already a lunch member"
#else
#	echo $(hostname) >> lunch_members
# 	git add lunch_members
#	git commit -m "added $(hostname) automatically"
#	git push
#	python lunch_updater.py #not necessary anymore
#fi

#execute right script depending on distribution here
echo ${DISTRIB_DESCRIPTION:0:6}

if [ "${DISTRIB_DESCRIPTION:0:6}" = "Ubuntu" ]; then
    unbuffer $LUNCHINATOR_DIR/indicator_applet.py --distrib-release=${DISTRIB_RELEASE} >> $LUNCHINATOR_CONFIG_DIR/lunch_calls.log
else
    echo "starting gtk-tray instead of indicator"
    unbuffer $LUNCHINATOR_DIR/gui_tray.py >> $LUNCHINATOR_CONFIG_DIR/lunch_calls.log
fi
#

