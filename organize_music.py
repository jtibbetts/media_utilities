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

# Globals
all_dirs = []
target_music_folder = None
all_track_info = None
track_location_dict = {}


def create_loid_segment(s):
    if s is None:
        return ''
    return str(s).replace(" ", "")

def create_playlist_dirname(playlist_name):
    if playlist_name.endswith("::"):
        playlist_name = playlist_name[0:-2]
    playlist_dirname = playlist_name.replace('::', '/')
    return re.sub(' +', '_', playlist_dirname)

def normalize_str(ustr):
    s = unicode_to_utf8(ustr)
    return re.sub( '\s+', ' ', s).strip()

def get_all_track_info(itlib):
    all_track_info = {}
    for id, track in itlib.songs.items():
        loid = get_track_loid(track)
        all_track_info[loid] = {'track': track, 'in_folders': []}
    return all_track_info

def get_original_files(target_folder_path):
    original_files = []
    for root, dirs, files in os.walk(target_folder_path):
        for file in files:
            full_file = root + '/' + file
            original_files.append(full_file)
    return original_files

def get_track_loid(track):
    loid = create_loid_segment(track.name)
    loid += '|'
    loid += create_loid_segment(track.composer)
    loid += '|'
    loid += create_loid_segment(track.album)
    loid += '|'
    loid += create_loid_segment(track.length)
    loid += '|'
    loid += create_loid_segment(track.size)
    return loid

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
        name = normalize_str(name)
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

def process_track_list(is_folder_not_playlist, track_list, m3u_entries, playlist_name):
    global target_music_folder,  all_track_info, track_location_dict
    counter = 0
    all_files = []

    for track in track_list:
        track_loid = get_track_loid(track)
        track_info = all_track_info[track_loid]
        if track_info == None:
            # shouldn't happen
            print "Error: track_loid " + track_loid + " could not be found"
            continue

        (track_name, track_name_display) = normalize_track_name(track.name)
        if is_folder_not_playlist:
            if "Bleecker" in track_name:
                pass
            source_location = '/' + track.location
            file_name, file_ext = os.path.splitext(source_location)
            playlist_dirname = create_playlist_dirname(playlist_name)
            relative_path = playlist_dirname + '/' + track_name + file_ext
            absolute_path = target_music_folder + '/' + relative_path
            if not os.path.isfile(absolute_path):
                shutil.copyfile(source_location, absolute_path)
            track_info['in_folders'].append(playlist_name)
            all_files.append(absolute_path)
            track_location_dict[track_loid] = relative_path
        else:
            in_folder_name = next(iter(track_info['in_folders']), None)
            if "Bleecker" in track_name:
                pass
            if in_folder_name == None:
                source_location = '/' + track.location
                file_name, file_ext = os.path.splitext(source_location)
                relative_path = 'Unassigned/' + track_name + file_ext
                absolute_path = target_music_folder + '/' + relative_path
                if not os.path.isfile(absolute_path):
                    unassigned_folder_name = target_music_folder + '/' + 'Unassigned'
                    if not os.path.exists(unassigned_folder_name):
                        mkdir_p(unassigned_folder_name)
                    shutil.copyfile(source_location, absolute_path)
                track_info['in_folders'].append(playlist_name)
                all_files.append(absolute_path)
                track_location_dict[track_loid] = relative_path
            else:
                source_location = '/' + track.location
                file_name, file_ext = os.path.splitext(source_location)
                playlist_dirname = create_playlist_dirname(in_folder_name)
                relative_path = playlist_dirname + '/' + ("%03d" % counter) + '-' + track.name + file_ext
                absolute_path = target_music_folder + '/' + relative_path
                all_files.append(absolute_path)


        length_in_seconds = int(math.ceil(track.length / 1000.0))
        m3u_entries.append([length_in_seconds, track_name_display, relative_path])

        counter += 1

    return all_files

def remove_old_files(target_folder_path, original_files, new_files):
    # remove files in folder that aren't in source (a la rsync --delete)
    for file in original_files:
        if not file in new_files:
            os.remove(file)
            print "Remove file " + file

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def unicode_to_utf8(ustr):
    if isinstance(ustr, unicode):
        result = unicodedata.normalize('NFKD', ustr).encode('utf8')
    else:
        result = ustr
    return result

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
    global target_music_folder,  all_track_info, track_location_dict

    usage_string = "organize_music.py -h <iTuneLibrary> <localMusicFolder>"

    try:
        opts, args = getopt.getopt(argv, "h:")
    except getopt.GetoptError as e:
        print str(e)
        print usage_string
        sys.exit(0)

    specific_playlist_name = None

    for opt, arg in opts:
        if opt == '-h':
            print "usage: " + usage_string
            sys.exit(0)

    if len(args) != 2:
        print "Wrong number of arguments: " + usage_string
        print usage_string
        sys.exit(0)

    itune_library_path = args[0]
    target_music_folder = args[1]
    if not os.path.exists(target_music_folder):
        os.makedirs(target_music_folder)

    print "Loading iTunes library from " + itune_library_path
    itlib = Library(itune_library_path)

    print "Getting all track info"
    all_track_info = get_all_track_info(itlib)

    # clear all m3a (playlist) files
    playlist_files = os.listdir(target_music_folder)
    for playlist_file in playlist_files:
        if playlist_file.endswith(".m3u"):
            os.remove(target_music_folder + '/' + playlist_file)

    # Folder creation
    print "Create folders"
    for playlist_name in itlib.getPlaylistNames():
        playlist_name = playlist_name.strip()
        # ignore playlists for the moment
        if playlist_name.startswith('Playlist::'):
            continue

        if "::" in playlist_name:
            display_playlist_name = playlist_name.replace('::', ' ').strip()

            m3u_entries = []

            playlist_dirname = create_playlist_dirname(playlist_name)
            full_dirname = target_music_folder + '/' + playlist_dirname
            mkdir_p(full_dirname)
            all_dirs.append(unicode_to_utf8(playlist_dirname))

            original_file_list = get_original_files(full_dirname)

            print "  Folder: " + playlist_name

            track_list = itlib.getPlaylist(playlist_name).tracks

            new_file_list = process_track_list(True, track_list, m3u_entries, playlist_name)

            remove_old_files(full_dirname, original_file_list, new_file_list)

            # write out M3U files
            local_m3u_path = target_music_folder + '/' + display_playlist_name + '.m3u'
            write_m3u(local_m3u_path, m3u_entries)

    # traverse local music folder and delete folders that are no longer used
    remove_dirs = []
    for root, dirs, files in os.walk(target_music_folder):
        if root == target_music_folder:
            continue
        hit = False
        for local_dir in all_dirs:
            local_full_dir = target_music_folder + '/' + local_dir
            if local_full_dir.startswith(unicode_to_utf8(root)):
                hit = True
                break
        if not hit:
            if not root.endswith("/Unassigned"):
                remove_dirs.append(root)
    for remove_dir in remove_dirs:
        print ("removing " + remove_dir)
        shutil.rmtree(remove_dir)


    print "Create playlists"
    unassigned_folder_name = target_music_folder + '/' + 'Unassigned'
    original_file_list = get_original_files(target_music_folder + '/' + 'Unassigned')
    all_new_files = []
    for playlist_name in itlib.getPlaylistNames():
        if playlist_name.startswith('Playlist::'):
            # trim Playlist prefix for display version
            display_playlist_name = playlist_name[len('Playlist::'):].replace('::', ' ').strip()

            m3u_entries = []

            print "  Playlist: " + display_playlist_name

            track_list = itlib.getPlaylist(playlist_name).tracks

            new_file_list = process_track_list(False, track_list, m3u_entries, playlist_name)
            all_new_files.extend(new_file_list)

            # write out M3U files
            local_m3u_path = target_music_folder + '/' + display_playlist_name + '.m3u'
            write_m3u(local_m3u_path, m3u_entries)

    remove_old_files(unassigned_folder_name, original_file_list, all_new_files)

    print "Done"
    sys.exit(0)



if __name__ == "__main__":
    main(sys.argv[1:])