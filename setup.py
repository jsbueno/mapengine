# coding: utf-8
# Author: João S. O. Bueno
# Projeto Jovem Hacker
# License: GPL v.3

from setuptools import setup

setup(
    name = "mapengine",
    version = "0.3a",
    packages = ["mapengine"],
    # install_requires=["pygame>=1.8"], # TODO: check how to work around current
    # unavailability of pygame through pip install
    package_data = {"": ["*.png", "*.gpl", "*.ora", "*.wav", "*.mp3", "*.ogg"]},
    include_package_data = True,
    zip_safe=False,

    author = "João S. O. Bueno",
    author_email = "gwidion@gmail.com",
    description = "base engine for development of map based 2D games - Pre-alpha",
    keywords = "game pygame engine 2d map enterteinament teaching",
    license = "GNU General Public License v3 or later (GPLv3+)",
    url = "https://github.com/jsbueno/mapengine",
)

