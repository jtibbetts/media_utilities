. ~/.bash_profile
python ~/git/media_utilities/organize_music.py ~/Music/iTunes/iTunes\ Music\ Library.xml ~/Music/music-jt
rsync -avz --delete -e ssh ~/Music/music-jt/ root@192.168.2.150:/volume1/music-jt