#!/usr/bin/env python

from subprocess import call
import sys
import time

for f in sys.argv[1:]:
    printing_cmd = ["lpr", "-P", "PDF", "-#", str(1), f]
    print printing_cmd
    call(printing_cmd)
    time.sleep(1)