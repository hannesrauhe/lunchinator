#!/bin/sh
. /etc/*release

#execute right script depending on distribution here
#echo $DISTRIB_DESCRIPTION
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
unbuffer $DIR/indicator_applet.py >> $HOME/.lunch_calls
