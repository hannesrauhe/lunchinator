#!/bin/bash

. /etc/*release

LUNCHINATOR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LUNCHINATOR_CONFIG_DIR=$HOME/.lunchinator
cd $LUNCHINATOR_DIR
mkdir -p $LUNCHINATOR_CONFIG_DIR
mv *.cfg $LUNCHINATOR_CONFIG_DIR

#update before starting
git stash
git pull

#if the python script created an update file, restart it after it closes
#create one for the first start to see if $LUNCHINATOR_CONFIG_DIR is writable
touch $LUNCHINATOR_CONFIG_DIR/update

while [ -f "$LUNCHINATOR_CONFIG_DIR/update" ]; do
    rm $LUNCHINATOR_CONFIG_DIR/update
    #execute right script depending on distribution here
    if [ "${DISTRIB_DESCRIPTION:0:6}" = "Ubuntu" ]; then
        unbuffer $LUNCHINATOR_DIR/indicator_applet.py --distrib-release=${DISTRIB_RELEASE} >> $LUNCHINATOR_CONFIG_DIR/lunch_calls.log
    else
        echo "starting gtk-tray instead of indicator"
        unbuffer $LUNCHINATOR_DIR/gui_tray.py >> $LUNCHINATOR_CONFIG_DIR/lunch_calls.log
    fi
done
#

