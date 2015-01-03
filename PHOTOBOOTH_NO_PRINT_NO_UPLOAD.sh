#!/bin/bash

#MOUNT=$(~/piggyphoto/mount.sh)
CONTINUE=1
while [ $CONTINUE -eq 1 ]; do
  ./photobooth.py .
  if [ $? -eq 0 ]; then
    CONTINUE=0;
  else
    sleep 5;
  fi
done;

echo "Press any key to exit"
read -n 1
