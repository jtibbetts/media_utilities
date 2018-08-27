
import os
import hashlib

try:
    import argparse
    argparser = argparse.ArgumentParser()
    argparser.add_argument("source_folder", help="Source folder")
    argparser.add_argument("--display", help="Display trace", default="false")
    args = argparser.parse_args()
except ImportError:
    args = None

image_map = {}

counter = 1
for root, dir, files in os.walk(args.source_folder):
    for file in files:

        file_name, file_ext = os.path.splitext(file)
        if file_ext == '.jpg':
            image_info = {}

            msg_digest = hashlib.sha256()
            msg_digest.update(file_name)

            oid = msg_digest.hexdigest()

            image_info['oid'] = oid
            image_info['name'] = file_name

            counter += 1

print counter