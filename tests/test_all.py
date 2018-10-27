import pytest
import tempfile
import pysortexif
import os

@pytest.fixture()
def cleandir():
    newpath = tempfile.mkdtemp()
    os.chdir(newpath)


@pytest.mark.usefixtures("cleandir")
class TestDirectoryInit(object):
    def test_cwd_starts_empty(self):
        assert 1


def test_paringdata():
    assert pysortexif.pysortexif.parse_date("") is None
