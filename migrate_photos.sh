#!/usr/bin/env bash
# remove 'old' photos from queue...then fill with new photos
find ~/Pictures/GPhotosUploadQueue/* -mtime +2 -exec rm {} \;

# sort all photos into AllPhotos
python ~/git/media_utilities/sortphotos.py -cr --sort %Y/%Y-%m-%b ~/Dropbox/Camera\ Uploads ~/Pictures/AllPhotos

mv ~/Dropbox/Camera\ Uploads/* ~/Pictures/GPhotosUploadQueue/.

# backup all photos
rsync -av --delete  ~/Pictures/AllPhotos/* root@kazan:/volume1/media/AllPhotos-$LOGNAME/.

