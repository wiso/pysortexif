import logging
import os
import shutil
from datetime import datetime

import pytest
from PIL import Image

import pysortexif
from pysortexif import pysortexif as p

HAS_EXIFTOOL = shutil.which("exiftool") is not None
needs_exiftool = pytest.mark.skipif(not HAS_EXIFTOOL, reason="exiftool not installed")


def make_jpeg(path, date_original=None, modify_date=None, color=(0, 0, 0)):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (4, 4), color)
    exif = image.getexif()
    if modify_date:
        exif[0x0132] = modify_date  # DateTime (EXIF:ModifyDate)
    if date_original:
        exif.get_ifd(0x8769)[0x9003] = date_original  # DateTimeOriginal
    image.save(path, exif=exif)
    return path


class FakeExifTool:
    """Stand-in for exiftool.ExifToolHelper returning fixed metadata."""

    def __init__(self, metadata=None):
        self.metadata = metadata or {}
        self.calls = []

    def get_metadata(self, filenames):
        self.calls.append(filenames)
        return [self.metadata]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# parse_date


def test_parse_date_valid():
    assert pysortexif.parse_date("2020:05:06 10:11:12") == datetime(
        2020, 5, 6, 10, 11, 12
    )


@pytest.mark.parametrize(
    "date_string",
    ["2020:05:06 10:11:12+02:00", "2020:05:06 10:11:12.123", " 2020:05:06 10:11:12 "],
)
def test_parse_date_ignores_subseconds_and_timezone(date_string):
    assert pysortexif.parse_date(date_string) == datetime(2020, 5, 6, 10, 11, 12)


@pytest.mark.parametrize(
    "date_string",
    ["", None, "0000:00:00 00:00:00", "not a date", "2020:13:01 00:00:00", 12],
)
def test_parse_date_invalid(date_string):
    assert pysortexif.parse_date(date_string) is None


# get_new_path


def test_get_new_path():
    assert p.get_new_path("out", datetime(2020, 5, 6, 10, 11, 12)) == os.path.join(
        "out", "2020/05/06"
    )


# filename_generator


def test_filename_generator_recursive(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "sub" / "deeper").mkdir(parents=True)
    (tmp_path / "sub" / "b.jpg").write_bytes(b"b")
    (tmp_path / "sub" / "deeper" / "c.jpg").write_bytes(b"c")
    files = list(p.filename_generator(str(tmp_path)))
    assert files == [
        str(tmp_path / "a.jpg"),
        str(tmp_path / "sub" / "b.jpg"),
        str(tmp_path / "sub" / "deeper" / "c.jpg"),
    ]


def test_filename_generator_special_characters(tmp_path):
    directory = tmp_path / "[photos]*?"
    directory.mkdir()
    (directory / "a.jpg").write_bytes(b"a")
    assert list(p.filename_generator(str(directory))) == [str(directory / "a.jpg")]


def test_filename_generator_exclude(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "b.jpg").write_bytes(b"b")
    files = list(p.filename_generator(str(tmp_path), exclude=str(tmp_path / "out")))
    assert files == [str(tmp_path / "a.jpg")]


def test_filename_generator_skips_non_files(tmp_path, caplog):
    (tmp_path / "a.jpg").write_bytes(b"a")
    os.symlink(tmp_path / "missing", tmp_path / "broken")
    with caplog.at_level(logging.INFO):
        files = list(p.filename_generator(str(tmp_path)))
    assert files == [str(tmp_path / "a.jpg")]
    assert "it is not a file" in caplog.text


# get_filename_date


def test_get_filename_date_exifread(tmp_path):
    image = make_jpeg(tmp_path / "a.jpg", date_original="2020:05:06 10:11:12")
    et = FakeExifTool()
    assert p.get_filename_date(str(image), et) == "2020:05:06 10:11:12"
    assert et.calls == []


def test_get_filename_date_exiftool_fallback(tmp_path):
    image = make_jpeg(tmp_path / "a.jpg")
    et = FakeExifTool({"EXIF:CreateDate": "2021:01:02 03:04:05"})
    assert p.get_filename_date(str(image), et) == "2021:01:02 03:04:05"


def test_get_filename_date_invalid_exifread_falls_back(tmp_path):
    image = make_jpeg(tmp_path / "a.jpg", date_original="0000:00:00 00:00:00")
    et = FakeExifTool({"EXIF:CreateDate": "2021:01:02 03:04:05"})
    assert p.get_filename_date(str(image), et) == "2021:01:02 03:04:05"


def test_get_filename_date_quicktime_invalid_falls_back(tmp_path):
    video = tmp_path / "a.mov"
    video.write_bytes(b"")
    et = FakeExifTool(
        {
            "QuickTime:CreateDate": "0000:00:00 00:00:00",
            "EXIF:ModifyDate": "2019:07:08 09:10:11",
        }
    )
    assert p.get_filename_date(str(video), et) == "2019:07:08 09:10:11"


def test_get_filename_date_prefers_capture_date(tmp_path):
    image = make_jpeg(tmp_path / "a.jpg")
    et = FakeExifTool(
        {
            "EXIF:ModifyDate": "2022:01:01 00:00:00",
            "EXIF:CreateDate": "2021:01:02 03:04:05",
        }
    )
    assert p.get_filename_date(str(image), et) == "2021:01:02 03:04:05"


def test_get_filename_date_modify_date_warns(tmp_path, caplog):
    image = make_jpeg(tmp_path / "a.jpg")
    et = FakeExifTool(
        {
            "EXIF:CreateDate": "0000:00:00 00:00:00",
            "EXIF:ModifyDate": "2022:01:01 00:00:00",
        }
    )
    assert p.get_filename_date(str(image), et) == "2022:01:01 00:00:00"
    assert "modification date" in caplog.text


def test_get_filename_date_none(tmp_path):
    text = tmp_path / "a.txt"
    text.write_text("hello")
    assert p.get_filename_date(str(text), FakeExifTool()) is None


def test_get_filename_date_quicktime(tmp_path):
    video = tmp_path / "a.mov"
    video.write_bytes(b"")
    et = FakeExifTool({"QuickTime:CreateDate": "2019:07:08 09:10:11"})
    assert p.get_filename_date(str(video), et) == "2019:07:08 09:10:11"


def test_get_filename_date_quicktime_missing(tmp_path):
    video = tmp_path / "a.mov"
    video.write_bytes(b"")
    assert p.get_filename_date(str(video), FakeExifTool()) is None


@needs_exiftool
def test_get_filename_date_real_exiftool(tmp_path):
    import exiftool

    image = make_jpeg(tmp_path / "a.jpg", modify_date="2018:02:03 04:05:06")
    with exiftool.ExifToolHelper() as et:
        assert p.get_filename_date(str(image), et) == "2018:02:03 04:05:06"


# copy_image


def test_copy_image_new(tmp_path):
    source = tmp_path / "in" / "a.jpg"
    source.parent.mkdir()
    source.write_bytes(b"data")
    dest_dir = tmp_path / "out" / "2020" / "05" / "06"
    assert p.copy_image(str(source), str(dest_dir))
    assert (dest_dir / "a.jpg").read_bytes() == b"data"
    assert source.exists()


def test_copy_image_remove_source(tmp_path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"data")
    dest_dir = tmp_path / "out"
    assert p.copy_image(str(source), str(dest_dir), remove_source=True)
    assert (dest_dir / "a.jpg").read_bytes() == b"data"
    assert not source.exists()


@pytest.mark.parametrize("remove_source", [False, True])
def test_copy_image_equal_exists(tmp_path, remove_source):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"data")
    dest_dir = tmp_path / "out"
    dest_dir.mkdir()
    (dest_dir / "a.jpg").write_bytes(b"data")
    assert p.copy_image(str(source), str(dest_dir), remove_source=remove_source)
    assert source.exists() != remove_source
    assert (dest_dir / "a.jpg").read_bytes() == b"data"


def test_copy_image_different_exists(tmp_path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"new")
    dest_dir = tmp_path / "out"
    dest_dir.mkdir()
    (dest_dir / "a.jpg").write_bytes(b"old")
    assert not p.copy_image(str(source), str(dest_dir), remove_source=True)
    assert (dest_dir / "a.jpg").read_bytes() == b"old"
    assert source.exists()


def test_copy_image_different_exists_overwrite(tmp_path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"new")
    dest_dir = tmp_path / "out"
    dest_dir.mkdir()
    (dest_dir / "a.jpg").write_bytes(b"old")
    assert p.copy_image(str(source), str(dest_dir), overwrite=True, remove_source=True)
    assert (dest_dir / "a.jpg").read_bytes() == b"new"
    assert not source.exists()


def test_copy_image_same_file(tmp_path):
    source = tmp_path / "a.jpg"
    source.write_bytes(b"data")
    assert p.copy_image(str(source), str(tmp_path), remove_source=True)
    assert source.read_bytes() == b"data"


# main


@pytest.fixture
def fake_exiftool(monkeypatch):
    et = FakeExifTool()
    monkeypatch.setattr(p.exiftool, "ExifToolHelper", lambda: et)
    monkeypatch.setattr(p.shutil, "which", lambda name: "/usr/bin/exiftool")
    return et


def test_main(tmp_path, fake_exiftool, caplog):
    make_jpeg(tmp_path / "in" / "a.jpg", date_original="2020:05:06 10:11:12")
    make_jpeg(tmp_path / "in" / "sub" / "b.jpg", date_original="2021:01:02 03:04:05")
    make_jpeg(tmp_path / "in" / "nodate.jpg")
    (tmp_path / "in" / "notes.txt").write_text("hello")
    caplog.set_level(logging.INFO)

    assert p.main([str(tmp_path / "in"), str(tmp_path / "out")]) == 0

    assert (tmp_path / "out" / "2020" / "05" / "06" / "a.jpg").exists()
    assert (tmp_path / "out" / "2021" / "01" / "02" / "b.jpg").exists()
    assert (tmp_path / "in" / "a.jpg").exists()
    assert "files copied: 2/4" in caplog.text
    assert "files not copied with no date: 2" in caplog.text


def test_main_remove_source_output_inside_input(tmp_path, fake_exiftool):
    make_jpeg(tmp_path / "a.jpg", date_original="2020:05:06 10:11:12")
    out = tmp_path / "sorted"
    make_jpeg(
        out / "2019" / "01" / "01" / "old.jpg", date_original="2019:01:01 00:00:00"
    )

    assert p.main([str(tmp_path), str(out), "--remove-source"]) == 0

    assert (out / "2020" / "05" / "06" / "a.jpg").exists()
    assert (out / "2019" / "01" / "01" / "old.jpg").exists()
    assert not (tmp_path / "a.jpg").exists()


def test_main_continues_after_error(tmp_path, fake_exiftool, monkeypatch, caplog):
    make_jpeg(tmp_path / "in" / "a.jpg", date_original="2020:05:06 10:11:12")
    make_jpeg(tmp_path / "in" / "b.jpg", date_original="2020:05:06 10:11:12")
    original = p.get_filename_date

    def failing(filename, et):
        if filename.endswith("a.jpg"):
            raise OSError("broken file")
        return original(filename, et)

    monkeypatch.setattr(p, "get_filename_date", failing)
    caplog.set_level(logging.INFO)

    assert p.main([str(tmp_path / "in"), str(tmp_path / "out")]) == 1
    assert (tmp_path / "out" / "2020" / "05" / "06" / "b.jpg").exists()
    assert "broken file" in caplog.text
    assert "files not copied because of errors: 1" in caplog.text


def test_main_missing_input(tmp_path, fake_exiftool):
    with pytest.raises(SystemExit):
        p.main([str(tmp_path / "missing"), str(tmp_path / "out")])


def test_main_missing_exiftool(tmp_path, monkeypatch):
    monkeypatch.setattr(p.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit):
        p.main([str(tmp_path), str(tmp_path / "out")])


@needs_exiftool
def test_main_real_exiftool(tmp_path):
    make_jpeg(tmp_path / "in" / "a.jpg", modify_date="2018:02:03 04:05:06")
    assert p.main([str(tmp_path / "in"), str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "2018" / "02" / "03" / "a.jpg").exists()


def test_main_different_file_exists(tmp_path, fake_exiftool, caplog):
    make_jpeg(tmp_path / "in" / "a.jpg", date_original="2020:05:06 10:11:12")
    make_jpeg(tmp_path / "out" / "2020" / "05" / "06" / "a.jpg", color=(255, 0, 0))
    caplog.set_level(logging.INFO)
    assert p.main([str(tmp_path / "in"), str(tmp_path / "out")]) == 0
    assert "files copied: 0/1" in caplog.text
