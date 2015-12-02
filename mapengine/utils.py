# coding: utf-8

import logging
import os, sys
logger = logging.getLogger(__name__)

def pwd(back=1):
    """retrieve working dir of the file where this function was called from - 
    or previous frames.
    Used to add directories to the search path of data files whenever a "Scene" is instantiated.
    """
    frame = sys._getframe()
    for i in range(back):
        frame = frame.f_back
    calling_module = frame.f_globals["__name__"]
    if calling_module == "__main__":
        # FIXME: get a way to findout where we where called from,
        # if from the main module
        return os.getcwd()
    return os.path.dirname(os.path.abspath(sys.modules[calling_module].__file__))


def plain_loader(path):
    with open(path, "rb") as file:
        return file.read()


def resource_load(filename, paths=None, cache=None, prefix=None, default=None, force=False, loader=None):
    if loader is None:
        loader = plain_loader
    if paths is None:
        paths = ["."]
    for directory in reversed(paths):
        path = os.path.join(directory, filename)
        if cache and path in cache and not force:
            logger.debug("Using cached resource for '{}'".format(path))
            return cache[path]
        if os.path.exists(path):
            break
    try:
        logger.debug("Loading resource at '{}'".format(path))
        resource = loader(path)
    except Exception as exc:
        resource = default
        if force:
            logger.error("Failed to load image at '{}' as well as path folders: {}. Error found: {}".format(path, paths, exc))
    if cache is not None:
        cache[path] = resource
    return resource


class Vector(object):
    __slots__ = ["x", "y"]

    def __init__(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index==0:
            return self.x
        if index==1:
            return self.y
        raise IndexError

    def __setitem__(self, index, value):
        if index == 0:
            self.x = value
        elif index == 1:
            self.y == value
        else:
            raise IndexError

    def __eq__(self, other):
        return self.x == other[0] and self.y == other[1]

    def __add__(self, other):
        return Vector((self.x + other[0], self.y + other[1]))

    def __radd__(self, other):
        return Vector((self.x + other[0], self.y + other[1]))

    def __sub__(self, other):
        return Vector((self.x - other[0], self.y - other[1]))

    def __mul__(self, other):
        return Vector((self.x * other, self.y * other))

    def __div__(self, other):
        return Vector((self.x // other, self.y // other))

    def __truediv__(self, other):
        return Vector((self.x / float(other), self.y / float(other)))

    def distance(self, other):
        return ((self.x - other[0]) ** 2, (self.y - other[1]) ** 2) ** 0.5

    def __repr__(self):
        return "Vector(({:g},{:g}))".format(self.x, self.y)

    def __hash__(self):
        return hash((self.x, self.y))

V = Vector
