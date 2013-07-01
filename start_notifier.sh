#!/bin/bash
#backward-compatibility you can use start_lunchinator.py instead of this script

#echo "This script is deprecated. Please use start_lunchinator.py to fire up the lunchinator."

LUNCHINATOR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LUNCHINATOR_CONFIG_DIR=$HOME/.lunchinator
cd $LUNCHINATOR_DIR
mkdir -p $LUNCHINATOR_CONFIG_DIR

./start_lunchinator.py
