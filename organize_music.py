#! /Users/johntibbetts/venv/dj18/bin/python

# rsync -avz --delete -e ssh ~/Music/music-jt/ root@192.168.2.150:/volume1/music-jt

import os
import sys
import getopt
import math

import re
import errno
import shutil

import unicodedata

from urlparse import urlparse

from pyItunes import *

reload(sys)
sys.setdefaultencoding('utf-8')

ITUNES_SUBFOLDER = "iTunes Music"

def create_playlist_dirname(playlist_name):
    if playlist_name.endswith("::"):
        playlist_name = playlist_name[0:-2]
    playlist_dirname = playlist_name.replace('::', '/')
    return re.sub(' +', '_', playlist_dirname)

def de_unicode(ustr):
    s = unicodedata.normalize("NFKD", ustr).encode('ascii', 'ignore')
    return re.sub( '\s+', ' ', s).strip()

def get_machine_specific_prefix(path):
    last_slash_pos = path.rfind('/')
    return path[0:last_slash_pos+1] + ITUNES_SUBFOLDER + '/'

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def normalize_track_name(name):
    if isinstance(name, unicode):
        name = de_unicode(name)
    name_with_blanks = name
    name = re.sub('\s+', '_', name)
    name = re.sub('\s*-\s*', '_', name)     # intervening ' - '
    name = re.sub('/', '_', name)
    name = re.sub('\\\\', '_', name)
    name = re.sub('\?', '_', name)
    name = re.sub(':', '_', name)
    name = re.sub('"', '_', name)
    name = re.sub('_+', '_', name)
    return (name, name_with_blanks)

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def write_m3u(path, entries):
    if len(entries) > 0:
        m3u_file = open(path, "wb")
        m3u_file.write("#EXTM3U\n")
        for entry in entries:
            outline = "#EXTINF:"
            outline += str(entry[0])
            outline += ','
            outline += entry[1]
            outline += '\n'
            outline += entry[2]
            outline += '\n'
            m3u_file.write(outline.encode('UTF-8'))
        m3u_file.close()


def main(argv):
    usage_string = "organize_music.py -h [-f <select folder>] <iTuneLibrary> <localMusicFolder> [<remoteMusicFolder>]"

    try:
        opts, args = getopt.getopt(argv, "hf:")
    except getopt.GetoptError as e:
        print str(e)
        print usage_string
        sys.exit(0)

    specific_playlist_name = None

    for opt, arg in opts:
        if opt == '-h':
            print "usage: " + usage_string
            sys.exit(0)
        elif opt == '-f':
            specific_playlist_name = arg

    if len(args) < 2 or len(args) > 3:
        print "Wrong number of arguments: " + usage_string
        print usage_string
        sys.exit(0)

    itune_library_path = args[0]
    local_music_folder = args[1]
    if len(args) > 2:
        remote_music_folder = args[2]
    else:
        remote_music_folder = None

    all_dirs = []

    local_playlist_folder = local_music_folder + '/' + 'local_playlists'
    if not os.path.exists(local_playlist_folder):
        os.makedirs(local_playlist_folder)

    remote_playlist_folder = local_music_folder + '/' + 'remote_playlists'
    if not os.path.exists(remote_playlist_folder):
        os.makedirs(remote_playlist_folder)

    machine_specific_prefix = get_machine_specific_prefix(itune_library_path)

    print "Loading iTunes library from " + itune_library_path
    itlib = Library(itune_library_path)

    for playlist_name in itlib.getPlaylistNames():
        if "::" in playlist_name:
            display_playlist_name = playlist_name.replace('::', ' ')

            local_m3u_entries = []
            remote_m3u_entries = []

            playlist_dirname = create_playlist_dirname(playlist_name)
            full_dirname = local_music_folder + '/' + playlist_dirname
            mkdir_p(full_dirname)
            all_dirs.append(playlist_dirname)

            # if specific_playlist_name and not this playlist
            if specific_playlist_name != None and specific_playlist_name != playlist_name:
                continue

            print "Playlist: " + playlist_name

            counter = 0
            all_files = []
            for track in itlib.getPlaylist(playlist_name).tracks:
                source_location = '/' + track.location
                file_name, file_ext = os.path.splitext(source_location)
                (track_name, track_name_display) = normalize_track_name(track.name)
                local_path = full_dirname + '/' + ("%03d" % counter) + '-' + track_name + file_ext
                if not os.path.isfile(local_path):
                    shutil.copyfile(source_location, local_path)
                all_files.append(local_path)

                length_in_seconds = int(math.ceil(track.length / 1000.0))
                local_m3u_entries.append([length_in_seconds, track_name_display, local_path])
                if remote_music_folder != None:
                    remote_path = remote_music_folder + '/' + playlist_dirname + '/' + ("%03d" % counter) + '-' + track_name + file_ext
                    remote_m3u_entries.append([length_in_seconds, track_name_display, remote_path])

                counter += 1

            # remove files in folder that aren't in source (a la rsync --delete)
            for root, dirs, files in os.walk(full_dirname):
                for file in files:
                    print "Walking " + file
                    full_file = full_dirname + '/' + file
                    if not full_file in all_files:
                        if os.path.exists(full_file):
                            # needed for more than 2-level nested folders
                            print "Removing file " + full_file
                            os.remove(full_file)

            # write out M3U files
            # local_m3u_path = local_playlist_folder + '/' + display_playlist_name + '.m3u'
            # write_m3u(local_m3u_path, local_m3u_entries)
            if remote_music_folder != None:
                remote_m3u_path = remote_playlist_folder + '/' + display_playlist_name + '.m3u'
                write_m3u(remote_m3u_path, remote_m3u_entries)

    # traverse local music folder and delete folders that are no longer used
    remove_dirs = []
    for root, dirs, files in os.walk(local_music_folder):
        if root == local_music_folder:
            continue
        hit = False
        for local_dir in all_dirs:
            local_full_dir = local_music_folder + '/' + local_dir
            if local_full_dir.startswith(root):
                hit = True
                break
        if not hit:
            if not root.endswith("_playlists"):
                remove_dirs.append(root)
    for remove_dir in remove_dirs:
        print ("removing " + remove_dir)
        shutil.rmtree(remove_dir)



    print "Done"
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])