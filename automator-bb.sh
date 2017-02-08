. ~/.bash_profile
python ~/git/media_utilities/organize_music.py ~/Music/iTunes/iTunes\ Music\ Library.xml ~/Music/music-bb
rsync -avz --delete -e ssh ~/Music/music-bb/ root@192.168.2.150:/volume1/music-bb