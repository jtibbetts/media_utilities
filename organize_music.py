#! /Users/johntibbetts/venv/dj18/bin/python
#
# """
# OrganizeMusic converts an iTunes library into external folders and links that can be imported
#     into Sonos or other music system (MS)
#
# Music systems will recognize folders of songs, or special .m3u files that are a collection links back into songs
# that live in those folders.
#
# To use this requires conventions be followed in iTunes:
#   1. Not all resources in iTunes need to be exported.  Only those that are desired to be recognized by the MS
#      They will be exported to the <local music folder> passed in as the first arg to this program.
#
#   2. Any iTunes Playlist that has name beginning with "Folder: ", or just "F:", will be moved into the external folder.
#       e.g. Folder: Musical Offering will create an external folder "Musical Offering"
#           Ditto F: Praetories to folder "Praetorius"
#      To ensure the music in the foldr is played in sequence (file systems don't impose order), the song will be
#      prefixed with "nnn-" as a sequence number.  e.g. 001-First Movement, 002-Second Movement, etc
#
#      To allow complex music libraries to exist Organize Music will allow folder structures to have deep paths.
#      e.g. F: Bach/Teldec/Motets will be put into an external folder Back/Teldec/Motets (under the <local-music-folder>
#
#   3. Any iTunes Playlist beginning with "Playlist:", or "P:", will be turned into a special ".m3u" file.
#      This is a file of links to the song.  Organize Music will find the song in a Folder (above) in a 2nd pass.
#      If the file hasn't been put into a folder it will add the song to an Unassigned/ folder.
#
#   4. Large multivolume music collections (e.g., Ring Cycle) can be specified as "Folder+Playlist:", or "F+P:".
#      This creates an ordered folder plus a playlist for it.  (This is a legacy feature...before songs were
#      sequenced in folders).
#
# At end of the harvesting process the <local music folder> should be copied to the target on some NAS.
# rsync -avz --delete -e ssh ~/Music/music-jt/ root@kazan:/volume1/music-jt
# """

import os
import sys
import getopt
import math

import re
import errno
import shutil

import unicodedata

from urlparse import urlparse

egg_path='/Users/johntibbetts/git/pyitunes/dist/pyItunes-1.4-py2.7.egg'

sys.path.append(egg_path)

from pyItunes import *

reload(sys)
sys.setdefaultencoding('utf-8')

ITUNES_SUBFOLDER = "iTunes Music"

# Globals
all_dirs = []
target_music_folder = None
all_track_info = None
track_location_dict = {}
all_new_files = []

def create_loid_segment(s):
    if s is None:
        return ''
    return str(s).replace(" ", "")

def create_per_folder_cache(folder_path):
    result = {}
    filenames = os.listdir(folder_path)
    for filename in filenames:
        (root, ext) = os.path.splitext(filename)
        zones = root.split('-')
        zones.pop(0)
        base_filename = '-'.join(zones)
        result[base_filename] = filename
    return result

def create_playlist_dirname(playlist_name):
    playlist_dirname = playlist_name.replace('::', '/')
    return re.sub(' +', '_', playlist_dirname)

def get_all_track_info(itlib):
    all_track_info = {}
    for id, track in itlib.songs.items():
        loid = get_track_loid(track)
        all_track_info[loid] = {'track': track, 'in_folders': []}
    return all_track_info

def get_original_files(target_folder_path):
    original_files = []
    for root, dirs, files in os.walk(target_folder_path):
        # only immediate subdirectory
        if root == target_folder_path:
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
        name = unicode_to_ascii(name)
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

def parse_playlist_name(playlist_name):
    prefix = ''
    zones = playlist_name.split(':')
    if len(zones) <= 1:
        pass
    else:
        prefix = parse_prefix(zones[0].strip().lower())
        if prefix != '':
            if len(zones) >= 2:
                playlist_name = ':'.join(zones[1:])
        else:
            prefix = ''
    playlist_name = playlist_name.strip()
    display_playlist_name = unicode_to_utf8(playlist_name.replace('/', ' ').strip())
    dir_playlist_name = unicode_to_ascii(playlist_name.replace(' ', '_')).strip()
    return [prefix, display_playlist_name, dir_playlist_name]

def parse_prefix(prefix):
    result = ''
    re_obj = re.match(r'^(\w+)(\W*)(\w+)?$', prefix)
    if re_obj != None:
        # two groups in regex
        str1 = parse_token(re_obj, 0)
        if str1 != '':
            result = str1
            str2 = parse_token(re_obj, 2)
            if str2 != '':
                result += ' ' + str2
    return result

def parse_token(re_obj, token_idx):
    result = ''
    check_value = re_obj.groups()[token_idx]
    if check_value != None:
        if 'folder'.startswith(check_value) or check_value == 'fldr':
            result = 'folder'
        elif 'playlist'.startswith(check_value):
            result = 'playlist'
    return result

def process_track_list(is_folder_not_playlist, track_list, m3u_entries, playlist_name):
    global target_music_folder,  all_track_info, track_location_dict
    counter = 0
    all_files = []

    per_folder_cache = {}

    for track in track_list:
        track_loid = get_track_loid(track)
        track_info = all_track_info[track_loid]
        if track_info == None:
            # shouldn't happen
            print "Error: track_loid " + track_loid + " could not be found"
            continue

        (track_name, track_name_display) = normalize_track_name(track.name)
        if is_folder_not_playlist:
            source_location = '/' + track.location
            file_name, file_ext = os.path.splitext(source_location)
            playlist_dirname = create_playlist_dirname(playlist_name)
            relative_path = playlist_dirname + '/' + ("%03d" % counter) + '-' + track_name + file_ext
            absolute_path = target_music_folder + '/' + relative_path
            if not os.path.isfile(absolute_path):
                shutil.copyfile(source_location, absolute_path)
            track_info['in_folders'].append(playlist_name)
            all_files.append(absolute_path)
            track_location_dict[track_loid] = relative_path
        else:
            in_folder_name = next(iter(track_info['in_folders']), None)
            if in_folder_name != None:
                absolute_folder_path = target_music_folder + '/' + in_folder_name
                if not os.path.exists(absolute_folder_path):
                    in_folder_name = None
            if in_folder_name == None:
                source_location = '/' + track.location
                file_name, file_ext = os.path.splitext(source_location)
                relative_path = 'Unassigned/' + ("%03d" % counter) + '-' + track_name + file_ext
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
                # already in some folder somewhere...build per-folder cache of track_names
                if not (in_folder_name in per_folder_cache):
                    # build cache
                    per_folder_cache[in_folder_name] = create_per_folder_cache(absolute_folder_path)

                folder_cache = per_folder_cache[in_folder_name]

                source_location = '/' + track.location
                file_name, file_ext = os.path.splitext(source_location)
                playlist_dirname = create_playlist_dirname(in_folder_name)
                prefixed_filename = folder_cache[track_name]
                if prefixed_filename == None:
                    print "Warning: can't find track for " + track_name
                    break
                relative_path = playlist_dirname + '/' + prefixed_filename


        length_in_seconds = int(math.ceil(track.length / 1000.0))
        m3u_entries.append([length_in_seconds, track_name_display, relative_path])

        counter += 1

    return all_files

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def unicode_to_ascii(ustr):
    if isinstance(ustr, unicode):
        result = unicodedata.normalize('NFKD', ustr).encode('ascii', 'ignore')
    else:
        result = ustr
    return result

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
    global target_music_folder,  all_track_info, track_location_dict, all_new_files

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

    # Folder creation -- folders are where a track lives
    print "Create folders"
    for raw_playlist_name in itlib.getPlaylistNames():
        (discriminator, display_playlist_name, dir_playlist_name) = parse_playlist_name(raw_playlist_name.strip())

        if 'folder' in discriminator:
            m3u_entries = []

            full_dirname = target_music_folder + '/' + dir_playlist_name
            mkdir_p(full_dirname)
            all_dirs.append(unicode_to_utf8(dir_playlist_name))

            original_file_list = get_original_files(full_dirname)

            print "  Folder: " + display_playlist_name

            track_list = itlib.getPlaylist(raw_playlist_name).tracks

            new_file_list = process_track_list(True, track_list, m3u_entries, dir_playlist_name)

            all_new_files.extend(new_file_list)

            # write out M3U files..but only if explicitly requested
            if 'playlist' in discriminator:
                local_m3u_path = target_music_folder + '/' + display_playlist_name + '.m3u'
                write_m3u(local_m3u_path, m3u_entries)

    # Playlists are links to folders ... the list of tracks are written to an .m3u files
    print "Create playlists"
    unassigned_folder_name = target_music_folder + '/' + 'Unassigned'
    original_file_list = get_original_files(target_music_folder + '/' + 'Unassigned')
    for raw_playlist_name in itlib.getPlaylistNames():
        (discriminator, display_playlist_name, dir_playlist_name) = parse_playlist_name(raw_playlist_name.strip())
        if 'playlist' in discriminator:
            m3u_entries = []

            print "  Playlist: " + display_playlist_name

            track_list = itlib.getPlaylist(raw_playlist_name).tracks

            new_file_list = process_track_list(False, track_list, m3u_entries, dir_playlist_name)
            all_new_files.extend(new_file_list)

            # write out M3U files
            local_m3u_path = target_music_folder + '/' + display_playlist_name + '.m3u'
            write_m3u(local_m3u_path, m3u_entries)

    # delete obsolete files, then any empty dirs
    for root, dirs, files in os.walk(target_music_folder):
        if root == target_music_folder:
            continue
        for file in files:
            if file == '.DS_Store':
                continue
            full_file = root + '/' + file
            if not full_file in all_new_files:
                os.remove(full_file)
                print "Remove file " + full_file

    for root, dirs, files in os.walk(target_music_folder):
        if root == target_music_folder:
            continue
        if len(files) == 0 and len(dirs) == 0:
            shutil.rmtree(root)

    print "Done"
    sys.exit(0)



if __name__ == "__main__":
    main(sys.argv[1:])