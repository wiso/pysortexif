[![CI](https://github.com/wiso/pysortexif/actions/workflows/ci.yml/badge.svg)](https://github.com/wiso/pysortexif/actions/workflows/ci.yml)

# pysortexif
Organize photographs in folders (`YYYY/MM/DD`) using exif information.

The date is taken from `EXIF DateTimeOriginal`; if missing, other dates are read with
[ExifTool](https://exiftool.org) (`CreateDate`, QuickTime `CreateDate` for videos and,
as a last resort, `ModifyDate`). Files without a valid date are left where they are.

## Requirements

- Python >= 3.14
- [ExifTool](https://exiftool.org) available in `PATH` (e.g. `apt install libimage-exiftool-perl`)

## How to install

    uv tool install pysortexif

or `pip install pysortexif`.

## Usage

    pysortexif INPUT_DIR OUTPUT_DIR [--overwrite] [--remove-source]

- `INPUT_DIR` is scanned recursively (the output directory is skipped if it is inside it).
- `--overwrite`: if a *different* file with the same name already exists in the destination, overwrite it (by default it is kept and the source is not copied).
- `--remove-source`: remove the source file after it is copied, or if an identical copy already exists (i.e. move instead of copy).

## Development

    uv sync
    uv run pytest
    uv run ruff check . && uv run ruff format --check .
