#!/usr/bin/env python

import argparse
import filecmp
import logging
import mimetypes
import os
import shutil
from datetime import datetime

import exifread
import exiftool

logger = logging.getLogger(__name__)

DATE_FORMAT = "%Y:%m:%d %H:%M:%S"

# ExifTool tags used when exifread does not find EXIF DateTimeOriginal,
# in order of preference. EXIF:ModifyDate is the last edit time, not the
# capture time, so it is only used as a last resort.
EXIFTOOL_DATE_TAGS = (
    "EXIF:DateTimeOriginal",
    "EXIF:CreateDate",
    "QuickTime:CreateDate",
    "EXIF:ModifyDate",
)


def filename_generator(directory_name, exclude=None):
    """Yield all files in directory_name, recursively.

    The directory exclude (e.g. the output directory, when it is inside the
    input directory) is not visited.
    """
    exclude = os.path.realpath(exclude) if exclude else None
    for root, dirnames, filenames in os.walk(directory_name):
        dirnames[:] = sorted(
            d for d in dirnames if os.path.realpath(os.path.join(root, d)) != exclude
        )
        for filename in sorted(filenames):
            path = os.path.join(root, filename)
            if not os.path.isfile(path):
                logger.info("ignoring %s, it is not a file", path)
                continue
            yield path


def get_quicktime_date(filename, et):
    metadata = et.get_metadata([filename])[0]
    return metadata.get("QuickTime:CreateDate")


def get_filename_date(filename, et):
    mime = mimetypes.guess_type(filename)

    if mime[0] == "video/quicktime":
        return get_quicktime_date(filename, et)

    with open(filename, "rb") as f:
        exif_data = exifread.process_file(
            f, stop_tag="EXIF DateTimeOriginal", details=False
        )
        date = exif_data.get("EXIF DateTimeOriginal", None)
        if date is not None:
            return date.values

    metadata = et.get_metadata([filename])[0]
    for tag in EXIFTOOL_DATE_TAGS:
        date = metadata.get(tag)
        if parse_date(date) is not None:
            if tag == "EXIF:ModifyDate":
                logger.warning(
                    "using modification date for %s, it may differ from capture date",
                    filename,
                )
            return date
    return None


def parse_date(date_string):
    """Parse an EXIF date ("YYYY:MM:DD HH:MM:SS"), ignoring subseconds and
    timezone. Return None if the date is missing or invalid."""
    if not date_string or not isinstance(date_string, str):
        return None
    try:
        return datetime.strptime(date_string.strip()[:19], DATE_FORMAT)
    except ValueError:
        return None


def get_new_path(basedir, date):
    return os.path.join(basedir, f"{date.year:04d}/{date.month:02d}/{date.day:02d}")


def copy_image(source, dest_dir, overwrite=False, remove_source=False):
    remove = os.remove if remove_source else (lambda x: None)
    action = "moving" if remove_source else "copying"
    dest = os.path.join(dest_dir, os.path.basename(source))
    if os.path.exists(dest) and os.path.samefile(source, dest):
        logger.info("%s is already in place, nothing to do", source)
        return True
    os.makedirs(dest_dir, exist_ok=True)
    if os.path.isfile(dest):
        if filecmp.cmp(source, dest, shallow=False):
            logger.info("filename %s already exists and it is equal, no copy", dest)
            remove(source)
            return True
        else:
            if overwrite:
                logger.info("overwriting %s with %s", dest, source)
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
        logger.info("%s file %s to %s", action, source, dest)
        shutil.copy2(source, dest)
        remove(source)
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Organize images in folders by day")
    parser.add_argument("input", help="input directory")
    parser.add_argument("output", help="output directory")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite the destination file if it exists and it is different "
        "(by default it is kept and the source is not copied)",
    )
    parser.add_argument(
        "--remove-source",
        action="store_true",
        help="remove the source file after it is copied (or if an identical "
        "copy already exists)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not os.path.isdir(args.input):
        parser.error(f"input directory {args.input} does not exist")
    if shutil.which("exiftool") is None:
        parser.error("exiftool not found, please install it (https://exiftool.org)")

    ncopied = 0
    nfiles = 0
    nnodate = 0
    nerrors = 0
    with exiftool.ExifToolHelper() as et:
        for fn in filename_generator(args.input, exclude=args.output):
            nfiles += 1
            try:
                date = parse_date(get_filename_date(fn, et))
                if date:
                    new_path = get_new_path(args.output, date)
                    if copy_image(
                        fn,
                        new_path,
                        overwrite=args.overwrite,
                        remove_source=args.remove_source,
                    ):
                        ncopied += 1
                else:
                    logger.info("no date for file %s", fn)
                    nnodate += 1
            except Exception as e:
                logger.error("error processing file %s: %s", fn, e)
                nerrors += 1
    logger.info("files copied: %d/%d", ncopied, nfiles)
    logger.info("files not copied with no date: %d", nnodate)
    if nerrors:
        logger.info("files not copied because of errors: %d", nerrors)
    return 1 if nerrors else 0


if __name__ == "__main__":
    raise SystemExit(main())
