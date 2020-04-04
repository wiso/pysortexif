import pysortexif


def test_match_filename():
    assert pysortexif.pysortexif.match_filename('myimage.jpg')
    assert pysortexif.pysortexif.match_filename('myimage.JPG')
    assert pysortexif.pysortexif.match_filename('myfolder/myimage.jpg')
    assert not pysortexif.pysortexif.match_filename('myimage.png')
    assert not pysortexif.pysortexif.match_filename('myfolder/myimage.jpg.png')
    assert pysortexif.pysortexif.match_filename('myfolder/myimage.jpg.png.JPG')


def test_paringdata():
    assert pysortexif.pysortexif.parse_date("") is None
