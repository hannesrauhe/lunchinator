#!/bin/bash

# usage: restart.sh process-id start_cmd

echo "Waiting for Lunchinator to exit..."
while kill -0 "$1" &>/dev/null; do
    sleep 0.5
done

echo "Launching Lunchinator"
eval "$2"
