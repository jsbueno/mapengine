# coding: utf-8

import logging

import pygame

from pygame.color import Color
from pygame.sprite import Sprite, Group

SIZE = 800, 600

logger = logging
logger.basicConfig()


class Directions(object):
    # TODO: create some simple const type with a nice REPR
    RIGHT, LEFT, UP, DOWN = (1, 0), (-1, 0), (0, -1), (0, 1)


class GameOver(Exception):
    pass


class Controller(object):
    def __init__(self, size, scene=None, **kw):
        self.width, self.height = self.size = size
        self.screen = pygame.display.set_mode(size, **kw)
        self.load_scene(scene)

    def load_scene(self, scene):
        self.scene = scene
        self.all_actors = Group()
        self.actors = {}
        self.load_initial_actors()

    def load_initial_actors(self):
        for x in range(self.scene.width):
            for y in range(self.scene.height):
                cls = self.scene.get_actor_at((x, y))
                if not cls:
                    continue
                name = cls.__name__.lower()
                actor = cls(self)
                actor.pos = (x, y)
                self.all_actors.add(actor)
                self.actors.setdefault(name, Group())
                self.actors[name].add(actor)
                if getattr(actor, "main_character", False):
                    self.set_main_character(actor)

    def set_main_character(self, actor):
        self.main_character = Group()
        self.main_character.add(actor)

    def update(self):
        self.scene.update()
        self.all_actors.update()
        self.draw()

    def draw(self):
        self.background()
        self.draw_actors()

    scale = property(lambda self: self.scene.blocksize)
    blocks_x = property(lambda self: self.width // self.scale)
    blocks_y = property(lambda self: self.height // self.scale)

    def background(self):
        scene = self.scene
        scale = self.scale
        for x in range(self.blocks_x):
            for y in range(self.blocks_y):
                image = scene[x + scene.left, y + scene.top]
                if isinstance(image, Color):
                    pygame.draw.rect(self.screen, image, (x * scale, y * scale, scale, scale))
                else:  # image
                    self.screen.blit(image, (x * scale, y * scale))

    def position_on_screen(self, pos):
        return (self.scene.left <= pos[0] < self.scene.left + self.blocks_x and
                self.scene.top <= pos[1] < self.scene.top + self.blocks_y)

    def draw_actors(self):
        scale = self.scene.blocksize
        for actor in self.all_actors:
            if not self.position_on_screen(actor.pos):
                continue
            x, y = actor.pos
            x -= self.scene.left
            y -= self.scene.top
            self.screen.blit(actor.image, (x * scale, y * scale))

    def quit(self):
        pygame.quit()


class Palette(object):
    """
    Loads a GIMP Palette file (.gpl) and keeps its
    data in an appropriate form for use of the rest of the application
    """
    def __init__(self, path):
        self.path = path
        self.colors = {}
        self.color_names = {}
        self.by_index = {}
        self.load()

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.color_names[key]
        elif isinstance(key, int):
            if key < 0:
                key = len(self.by_index) + key
            return self.by_index[key]
        if isinstance(key, Color):
            key = tuple(key)
        if len(key) == 3:
            key = key + (255,)
        return self.colors[key]

    def __len__(self):
        return len(self.colors)

    def __repr__(self):
        return '<Palette {!r}>'.format(self.color_names)

    def load(self):
        with open(self.path) as file_:
            line = ""
            while not line.strip().startswith('#'):
                line = next(file_)
            index = 0
            for line in file_:
                line = line.strip()
                if len(line.split()) < 4 or line.startswith('#'):
                    continue
                r, g, b, name = line.strip().split(None, 4)
                color = Color(*(int(component) for component in (r, g, b)))
                self.colors[tuple(color)] = name
                self.color_names[name] = color
                self.by_index[index] = color
                index += 1


class Scene(object):
    scene_path_prefix = "scenes/"
    out_of_map = Color(0, 0, 0)
    attributes = """
    top 0
    left 0
    target_top self.top
    target_left self.left
    margin 3
    h_margin self.margin
    v_margin self.margin

    display_size None
    window_width 16
    window_height 12

    scroll_rate 8

    out_of_map self.out_of_map
    actor_plane_sufix _actors

    """

    def __init__(self, scene_name, **kw):
        # FIXME: allow different extensions, attempt to file-name case sensitiveness
        self.scene_name = scene_name
        self.mapfile = scene_name + ".png"
        self.mapdescription = scene_name + ".gpl"

        # TODO: factor this out to a mixin "autoattr" class
        for line in self.attributes.split("\n"):
            line = line.strip("\x20\x09,")
            if not line or line[0].startswith("#"):
                continue
            attr, value = line.split(None, 1)
            self.load_attr(attr, value, kw)

        self.load()
        self.tiles = {}

        if not self.display_size:
            self.display_size = SIZE

        self.blocksize = self.display_size[0] // self.window_width

        self.scroll_count = 0

    def load_attr(self, attrname, default, kw):
        if isinstance(default, str):
            if default.isdigit():
                default = int(default)
            elif default.startswith("self."):
                default = getattr(self, default[len("self."):])
            elif default == "None":
                default = None
        setattr(self, attrname, kw.get(attrname, default))

    def load(self):
        self.image = pygame.image.load(self.scene_path_prefix + self.mapfile)
        try:
            self.actor_plane = pygame.image.load(self.scene_path_prefix + self.scene_name + self.actor_plane_sufix + ".png")
        except (pygame.error, IOError):
            self.actor_plane = pygame.surface.Surface((1, 1))
            logger.error("Could not find character plane for scene {}".format(self.scene_name))
        self.palette = Palette(self.scene_path_prefix + self.mapdescription)
        self.width, self.height = self.image.get_size()

    def __getitem__(self, position):
        try:
            color = self.image.get_at(position)
        except IndexError:
            return self.out_of_map
        # TODO: load scene block images
        try:
            name = self.palette[color]
        except KeyError:
            return color
        try:
            return self.tiles[name]
        except KeyError:
            pass

        try:
            img = pygame.image.load(self.scene_path_prefix + name + ".png")
        except (pygame.error, IOError):
            self.tiles[name] = color
        else:
            if img.get_width() != self.blocksize:
                ratio = float(self.blocksize) / img.get_width()
                img = pygame.transform.rotozoom(img, 0, ratio)
            self.tiles[name] = img
        return self.tiles[name]

    def get_actor_at(self, position):
        """
        At scene load all positions are scanned for actor instantiation.
        This is called by the controller automatically for each position on the map.
        """
        try:
            color = self.actor_plane.get_at(position)
        except IndexError:
            return None
        # for transparency colors, no actor:
        if color[3] == 0:
            return None
        # TODO: load scene block images
        try:
            name = self.palette[color]
        except KeyError:
            # Unregistered actor
            return None
        return GameObjectClasses.get(name, name)

    def move(self, direction):
        self.target_left += direction[0]
        self.target_top += direction[1]

        if self.target_left < - self.h_margin:
            self.target_left = - self.h_margin
        elif self.target_left > self.width - self.window_width + self.h_margin:
            self.target_left = self.width - self.window_width + self.h_margin
        if self.target_top < - self.v_margin:
            self.target_top = -self.v_margin
        elif self.target_top > self.height - self.window_height + self.v_margin:
            self.target_top = self.height - self.window_height + self.v_margin

    def update(self):
        self.scroll_count += 1
        if not self.scroll_count % self.scroll_rate:
            return
        self.scroll_count = 0
        if self.top < self.target_top:
            self.top += 1
        elif self.top > self.target_top:
            self.top -= 1
        if self.left < self.target_left:
            self.left += 1
        elif self.left > self.target_left:
            self.left -= 1


GameObjectClasses = {}


class GameObjectRegistry(type):
    def __new__(metacls, name, bases, dct):
        cls = type.__new__(metacls, name, bases, dct)
        GameObjectClasses[name.lower()] = cls
        return cls


class GameObject(Sprite):
    __metaclass__ = GameObjectRegistry

    def __init__(self, controller):
        self.controller = controller
        # TODO: allow for more sofisticated image loading
        self.image_path = self.controller.scene.scene_path_prefix + self.__class__.__name__.lower() + ".png"
        img = pygame.image.load(self.image_path)
        if controller.scene.blocksize != img.get_width():
            ratio = float(controller.scene.blocksize) / img.get_width()
            img = pygame.transform.rotozoom(img, 0, ratio)
        self.image = img
        super(GameObject, self).__init__()


####
# From here on, example and testing code:


class Actor(GameObject):
    pass


class Hero(Actor):
    main_character = True


class Animal0(Actor):
    pass


def main():
    scene = Scene('scene0')
    cont = Controller(SIZE, scene)
    try:
        while True:
            pygame.event.pump()
            cont.update()
            cont.draw()
            pygame.display.flip()
            pygame.time.delay(30)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                raise GameOver
            for direction in "RIGHT LEFT UP DOWN".split():
                if keys[getattr(pygame, "K_" + direction)]:
                    scene.move(getattr(Directions, direction))

    except GameOver:
        # cont.scene = EndGameScene()
        pass
    finally:
        cont.quit()


if __name__ == "__main__":
    main()

