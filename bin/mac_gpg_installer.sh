#!/bin/bash

INSTALLER_DMG="$1"

MOUNT="$(mktemp -d -t gpginstall)"
echo "$INSTALLER_DMG" 1>&2
if ! hdiutil attach -nobrowse -mountpoint "$MOUNT" "$INSTALLER_DMG"
then
	rmdir "$MOUNT"
	exit 1
fi

INSTALLER="$(find "$MOUNT" -iname *.pkg)"
if [ "$INSTALLER" == "" ]
then
	EXIT_CODE=1
else
	osascript -e "do shell script \"installer -pkg '$INSTALLER' -target /\" with administrator privileges"
	EXIT_CODE=$?
fi

hdiutil detach -quiet "$MOUNT"
rmdir "$MOUNT"

exit $EXIT_CODE
