#coding: utf-8

import os

from .utils import resource_load
from .global_states import SCENE_PATH

import pygame

class FontLoader(object):
    font_cache = {}

    font_prefix = "fonts/"
    def __init__(self, font_file_name="sans.ttf", size=16, bold=True, **kw):
        self.size = size
        paths = [os.path.join(path.rstrip("/").rsplit("/",1)[0], self.font_prefix) for path in SCENE_PATH]
        self.font = resource_load(font_file_name, paths=paths, cache=self.font_cache, loader=self.loader)
        self.font.set_bold(bold)
        self.color = kw.get("color", (255,255,255))
        self.antialias = kw.get("antialias", True)

    def loader(self, path):
        return pygame.font.Font(path, self.size)