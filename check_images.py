#! /Users/johntibbetts/venv/dj18/bin/python

import os
import sys
from PIL import Image

LOGGING = {}

def usage():
    print "usage: check_images sourceDir"

def main(args):
    sourceDir = args[0]
    types = ['.jpg', '.jpeg', '.png']
    count = 0
    for root, dirs, files in os.walk(sourceDir):
        for file in files:
            if file.lower().endswith(tuple(types)):
                filename = root + "/" + file
                count += 1
                try:
                    img = Image.open(filename)
                except:
                    print("Bad image: ", filename)

    print "Count: " + str(count)

if __name__=='__main__':

    if len(sys.argv) != 2:
        usage()
        sys.exit(2)

    main(sys.argv[1:])