#! /Users/johntibbetts/venv/dj18/bin/python

import os
import sys
import time
from shutil import copyfile

def usage():
    print "usage: delta_images sourceDir targetDir diffDir"

def main(sourceDir, textDir, diffDir):
    types = ['.jpg', '.jpeg', '.png']

    # gather target filenames
    targetFilenames = []
    for root, dirs, files in os.walk(targetDir):
        for file in files:
            if file.lower().endswith(tuple(types)):
                targetFilenames.append(file)
    print "targetCount: " + str(len(targetFilenames))

    # gather source dictionary
    sourceFileDict = {}
    for root, dirs, files in os.walk(sourceDir):
        for file in files:
            if file.lower().endswith(tuple(types)):
                sourceFileDict[file] = root + "/" + file

    print "sourceCount: " + str(len(sourceFileDict))

    # find missing source files in target
    missingSourceDict = {}
    for testFilename in sourceFileDict.keys():
        if not (testFilename in targetFilenames):
            missingSourceDict[testFilename] = sourceFileDict[testFilename]

    print "missingSource: " + str(len(missingSourceDict))

    # create file of deltas
    if not os.path.exists(diffDir):
        os.makedirs(diffDir)
    diffCounter = 0
    for filename in missingSourceDict.keys():
        sourcePath = sourceFileDict[filename]
        copyfile(sourcePath, diffDir + '/' + filename)
        diffCounter += 1

    print str(diffCounter) + " files written to " + diffDir



    # from collections import Counter
    #
    # sourceCounter = Counter(sourceFileDict.keys())
    # targetCounter = Counter(targetFilenames)

    print 'done'

if __name__=='__main__':
    args = sys.argv[1:]
    if len(args) != 2:
        usage()
        sys.exit(2)

    sourceDir = args[0]
    targetDir = args[1]
    diffDir = os.path.expanduser("~/Pictures/DiffPhotosAt" +  time.strftime('%Y-%m-%d--%H:%M:%S'))

    main(sourceDir, targetDir, diffDir)