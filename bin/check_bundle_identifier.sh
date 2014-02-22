#!/bin/bash

APPLESCRIPT=`cat <<EOF
on run argv
  try
    tell application "Finder"
      set appname to name of application file id "$1"
      return 1
    end tell
  on error err_msg number err_num
    return 0
  end try
end run
EOF`

retcode=`osascript -e "$APPLESCRIPT"`
exit $retcode
