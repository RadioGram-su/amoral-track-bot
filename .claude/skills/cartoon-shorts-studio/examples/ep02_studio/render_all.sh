#!/bin/bash
cd "$(dirname "$0")"
q1="dive chip heat power"; q2="hall scale cool ret"
run() { for sh in $1; do xvfb-run -a -s "-screen 0 1280x1024x24" blender -b --factory-startup -P short.py -- frames $sh >> log_$2.txt 2>&1; echo "DONE $sh" >> log_$2.txt; done; }
run "$q1" 1 & run "$q2" 2 & wait
echo ALLDONE
