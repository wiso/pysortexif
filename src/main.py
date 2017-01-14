import exifread
import os
from dateutil import parser
from datetime import datetime
import shutil
import filecmp

import logging

# create logger
logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

logger.addHandler(ch)

def match_filename(filename):
    return '.jpg' in filename or '.JPG' in filename

def filename_generator_python2(directory_name):
    import os

    matches = []
    for root, dirnames, filenames in os.walk(directory_name):
        for filename in filenames:
            yield os.path.join(root, filename)

def filename_generator_python3(directory_name):
    import glob
    def either(c):
        return '[%s%s]' % (c.lower(),c.upper()) if c.isalpha() else c
    for filename in glob.iglob('{0}/**/*.{1}'.format(directory_name, 'jpg'), recursive=True):
        yield filename

def filename_generator(directory_name):
    import sys
    if sys.version_info >= (3, 5):
        return filename_generator_python3(directory_name)
    else:
        return filename_generator_python2(directory_name)
    
def get_filename_date(filename):
    with open(filename, 'rb') as f:
        exif_data = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal')
        date = exif_data.get('EXIF DateTimeOriginal', None)
        if date:
            return date.values

def parse_date(date_string):
    if not date_string:
        return None
    return datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")

def get_new_path(basedir, date):
    return os.path.join(basedir, '{:04d}/{:02d}/{:02d}'.format(date.year, date.month, date.day))

def copy_image(source, dest_dir):
    dest = os.path.join(dest_dir, os.path.basename(source))
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if os.path.isfile(dest):
        if filecmp.cmp(source, dest, shallow=False):
            logger.info("filename %s already exists and it is equal, no copy", dest)
        else:
            logger.warning("filename %s already exists and it is different, no cpy is done", dest)
    else:
        logger.info("moving file %s to %s", fn, new_path)
        #shutil.copy2(source, dest)

if __name__ == "__main__":
    input_directory = "/var/run/media/turra/SamsungRugg/Immagini/"
    output_directory = '/tmp'
    output_directory = input_directory
    for fn in filename_generator(input_directory):
        date  = get_filename_date(fn)
        date = parse_date(date)
        if date:
            new_path = get_new_path(output_directory, date)
            copy_image(fn, new_path)
        else:
            logger.info("no date for file %s", fn)

