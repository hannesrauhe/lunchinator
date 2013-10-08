#!/bin/sh

# This script is called by indicator-applet.py automatically. If you prefer another icon,
# you can call this script manually, e.g.
#    sudo ./install-lunch-icons.sh lunch
#    sudo ./install-lunch-icons.sh clock

ICON_BASE="$1"

cd "$( dirname "$0" )"
echo "Base: '$ICON_BASE'"

# install icons for mono-dark (yes, the 'light' icon is for the dark theme)
cp ../images/${ICON_BASE}light.svg /usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg
cp ../images/${ICON_BASE}red.svg /usr/share/icons/ubuntu-mono-dark/status/24/lunchinatorred.svg

# install icons for mono-light
cp ../images/${ICON_BASE}.svg /usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg
cp ../images/${ICON_BASE}red.svg /usr/share/icons/ubuntu-mono-light/status/24/lunchinatorred.svg

# update icon caches
gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light
gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark
