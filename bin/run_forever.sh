#!/bin/sh

LUNCHINATOR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LUNCHINATOR_CONFIG_DIR=$HOME/.lunchinator
cd $LUNCHINATOR_DIR
mkdir -p $LUNCHINATOR_CONFIG_DIR

while test $? -ne 3; do
	git pull;
	git --git-dir=~/.lunchinator/plugins/.git pull
	python ./noninteractive.py --autoUpdate;
done
