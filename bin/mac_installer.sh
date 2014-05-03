#!/bin/bash

# usage: mac_installer.sh tarball target process-id

echo "Extracting update..."
tmpdir=$(mktemp -d -t lunchinator)
tar xjf "$1" -C "$tmpdir"

echo "Waiting for Lunchinator to exit..."
while kill -0 "$3" &>/dev/null; do
    sleep 0.5
done

echo "Replacing Lunchinator..."
if rm -rf "$2"
then
	mv "${tmpdir}/Lunchinator.app" "$2"
else
	echo "ERROR: could not remove old application"
fi

rm -rf "$tmpdir"
