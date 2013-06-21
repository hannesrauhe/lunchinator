#!/bin/sh

# install icons for mono-dark (yes, the 'light' icon is for the dark theme)
cp images/alarmlight.svg /usr/share/icons/ubuntu-mono-dark/status/24/lunchinator.svg
cp images/alarmred.svg /usr/share/icons/ubuntu-mono-dark/status/24/lunchinatorred.svg

# install icons for mono-light
cp images/alarm.svg /usr/share/icons/ubuntu-mono-light/status/24/lunchinator.svg
cp images/alarmred.svg /usr/share/icons/ubuntu-mono-light/status/24/lunchinatorred.svg

gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light
gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark
