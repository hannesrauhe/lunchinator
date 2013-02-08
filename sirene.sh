#!/bin/bash
tempo=33; slope=10; maxfreq=888; nu_beeps=95; function sinus { echo "s($1/$slope)*$maxfreq"|bc -l|tr -d "-"; }; for((i=1;i<nu_beeps;i++)); do beep -l$tempo -f`sinus $i`; done
