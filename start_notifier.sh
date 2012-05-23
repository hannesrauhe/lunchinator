#!/bin/bash

. /etc/*release

#execute right script depending on distribution here
#echo $DISTRIB_DESCRIPTION
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

unbuffer $DIR/indicator_applet.py >> $HOME/.lunch_calls


