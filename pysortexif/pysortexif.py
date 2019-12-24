import mimetypes
import exifread
import exiftool
import os
from datetime import datetime
import shutil
import filecmp

import logging

# create logger
logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

logger.addHandler(ch)


def match_filename(filename):
    _, ext = os.path.splitext(filename)
    return ".jpg" in ext or ".JPG" in ext


def filename_generator_python2(directory_name):
    import os

    for root, dirnames, filenames in os.walk(directory_name):
        for filename in filenames:
            if not os.path.isfile(filename):
                logger.info("ignoring %s, it is not a file")
                continue
            yield os.path.join(root, filename)


def filename_generator_python3(directory_name):
    import glob
    import os

    def either(c):
        return "[%s%s]" % (c.lower(), c.upper()) if c.isalpha() else c

    for filename in glob.iglob(
        "{0}/*".format(directory_name), recursive=True
    ):
        if not os.path.isfile(filename):
            logger.info("ignoring %s, it is not a file")
            continue
        yield filename


def filename_generator(directory_name):
    import sys

    if sys.version_info >= (3, 5):
        return filename_generator_python3(directory_name)
    else:
        return filename_generator_python2(directory_name)


def get_quicktime_date(filename):
    with exiftool.ExifTool() as et: 
        metadata = et.get_metadata_batch([filename])[0]
        return metadata["QuickTime:CreateDate"]

    
def get_filename_date(filename):
    mime = mimetypes.guess_type(filename)

    if mime[0] == "video/quicktime":
        return get_quicktime_date(filename)
    
    with open(filename, "rb") as f:
        exif_data = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal")
        date = exif_data.get("EXIF DateTimeOriginal", None)
        if date is not None:
            return date.values

    with exiftool.ExifTool() as et:
        metadata = et.get_metadata_batch([filename])[0]
        date = metadata.get('EXIF:ModifyDate', None)
        return date


def parse_date(date_string):
    if not date_string:
        return None
    return datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")


def get_new_path(basedir, date):
    return os.path.join(
        basedir, "{:04d}/{:02d}/{:02d}".format(date.year, date.month, date.day)
    )


def copy_image(source, dest_dir, overwrite=False, remove_source=False):
    remove = os.remove if remove_source else (lambda x: None)
    dest = os.path.join(dest_dir, os.path.basename(source))
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if os.path.isfile(dest):
        if filecmp.cmp(source, dest, shallow=False):
            logger.info("filename %s already exists and it is equal, no copy", dest)
            remove(source)
            return True
        else:
            if overwrite:
                logger.info("moving file %s to %s", fn, new_path)
                shutil.copy2(source, dest)
                remove(source)
                return True
            else:
                logger.warning(
                    "filename %s already exists and it is different, no copy is done",
                    dest,
                )
                return False
    else:
        logger.info("moving file %s to %s", fn, new_path)
        shutil.copy2(source, dest)
        remove(source)
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Organize images in forders by day")
    parser.add_argument("input", help="input directory")
    parser.add_argument("output", help="output directory")
    parser.add_argument(
        "--overwrite", action="store_true", help="overwrite if same image exists"
    )
    parser.add_argument("--remove-source", action="store_true", help="remove source")
    args = parser.parse_args()

    input_directory = args.input
    output_directory = args.output
    ncopied = 0
    nfiles = 0
    nnodate = 0
    for fn in filename_generator(input_directory):
        nfiles += 1
        date = get_filename_date(fn)
        date = parse_date(date)
        if date:
            new_path = get_new_path(output_directory, date)
            if copy_image(
                fn, new_path, overwrite=args.overwrite, remove_source=args.remove_source
            ):
                ncopied += 1
        else:
            logger.info("no date for file %s", fn)
            nnodate += 1
    logger.info("files copied: %d/%d", ncopied, nfiles)
    logger.info("files not copied with no date: %d" % nnodate)
