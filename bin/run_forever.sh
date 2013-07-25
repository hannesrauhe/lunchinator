#!/bin/sh

LUNCHINATOR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LUNCHINATOR_CONFIG_DIR=$HOME/.lunchinator
cd $LUNCHINATOR_DIR
mkdir -p $LUNCHINATOR_CONFIG_DIR

while true; do
	git pull;
	python ./noninteractive.py --autoUpdate;
done
