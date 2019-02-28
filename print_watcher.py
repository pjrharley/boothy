#!/usr/bin/env python2

import argparse
import logging
import os
import time
import sys
from printer import CmdPrinter, PyPrinter

logger = logging.getLogger('photobooth')

file_log_handler = logging.FileHandler('printer.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_log_handler.setFormatter(formatter)
logger.addHandler(file_log_handler)

stdout_log_handler = logging.StreamHandler(sys.stdout)
stdout_log_handler.setLevel(logging.WARN)
logger.addHandler(stdout_log_handler)

logger.setLevel(logging.DEBUG)

def watch_for_files(input_folder, printer):
    done_file = os.path.join(input_folder, 'done.txt')
    if not os.path.exists(done_file):
        open(done_file, 'a').close()
    with open(done_file) as f:
        content = f.readlines()
    done_files = set([x.strip() for x in content])
    while True:
        files = os.listdir(input_folder)
        jpgs = set([f for f in files if f.endswith('.jpg')])
        for jpg in jpgs:
            if jpg not in done_files:
                printer.print_image(os.path.join(input_folder, jpg))
                with open(done_file, 'a') as f:
                    f.write(jpg + '\n')
                done_files.add(jpg)
        time.sleep(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("print_from", help="Location to find images")
    parser.add_argument("-p", "--print_count",
                        help="Set number of copies to print", type=int, default=1)
    parser.add_argument("-P", "--printer", help="Set printer to use")
    args = parser.parse_args()

    logger.info("Args were: %s", args)
    printer = PyPrinter(args.printer, args.print_count, False)
    watch_for_files(args.print_from, printer)
