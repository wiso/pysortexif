import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pysortexif",
    version="0.1.0",
    author="Ruggero Turra",
    author_email="giurrero@gmail.com",
    description="Simple package to move photographs to folders, depending on exif timestamp",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wiso/pysortexif",
    packages=setuptools.find_packages(),
    install_requires=['exifread', 'pyexiftool'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2",
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
    ],
)
