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
            print "ugh - ", path
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