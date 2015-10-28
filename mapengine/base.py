# coding: utf-8

import logging

import pygame

from pygame.color import Color
from pygame.sprite import Sprite, Group

SIZE = 800, 600
FRAME_DELAY = 30

logger = logging
logger.basicConfig()


class Directions(object):
    # TODO: create some simple const type with a nice REPR
    RIGHT, LEFT, UP, DOWN = (1, 0), (-1, 0), (0, -1), (0, 1)

PAUSE = (0,0)

class GameOver(Exception):
    pass


class Controller(object):
    def __init__(self, size, scene=None, **kw):
        self.width, self.height = self.size = size
        self.screen = pygame.display.set_mode(size, **kw)
        self.actor_positions = {}
        self.load_scene(scene)

        self.old_top = -20
        self.old_left = -20
        self.old_tiles = {}
        self.dirty_tiles = {}


    def load_scene(self, scene):
        self.scene = scene
        scene.set_controller(self)
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
                actor = cls(self, pos=(x, y))
                self.all_actors.add(actor)
                self.actors.setdefault(name, Group())
                self.actors[name].add(actor)
                if getattr(actor, "main_character", False):
                    self.set_main_character(actor)

    def set_main_character(self, actor):
        self.main_character = Group()
        self.main_character.add(actor)

    @staticmethod
    def _touch(actor1, actor2):
        if actor1 is actor2:
            return False
        return actor1.rect.colliderect(actor2.rect)

    def update(self):
        self.scene.update()
        self.all_actors.update()
        for actor in self.all_actors:
            for collision in pygame.sprite.spritecollide(actor, self.all_actors, False, collided=self._touch):
                actor.on_over(collision)
            if isinstance(self.scene[actor.pos], GameObject):
                self.scene[actor.pos].on_over(actor)
        self.draw()

    def draw(self):
        self.background()
        self.draw_actors()

    scale = property(lambda self: self.scene.blocksize)
    # These hold the on-screen size of the game-scene in blocks
    blocks_x = property(lambda self: self.width // self.scale)
    blocks_y = property(lambda self: self.height // self.scale)

    def background(self):
        scene = self.scene
        scale = self.scale
        for x in range(self.blocks_x):
            for y in range(self.blocks_y):
                obj = scene[x + scene.left, y + scene.top]
                image = obj.image if hasattr(obj, "image") else obj
                self._draw_tile_at((x,y), image)
        # TODO: Use these to further improve background caching, but for
        # games with animated background.
        self.old_top = scene.top
        self.old_left = scene.left

    def _draw_tile_at(self, (x,y), image):
        scale = self.scale
        if self.old_tiles.get((x,y), None) is image and not self.dirty_tiles.get((x, y), True):
            return
        if isinstance(image, Color):
            pygame.draw.rect(self.screen, image, (x * scale, y * scale, scale, scale))
        else:  # image
            self.screen.blit(image, (x * scale, y * scale))
        self.old_tiles[x, y] = image
        self.dirty_tiles[x, y] = False

    def position_on_screen(self, pos):
        return (self.scene.left <= pos[0] < self.scene.left + self.blocks_x and
                self.scene.top <= pos[1] < self.scene.top + self.blocks_y)

    def draw_actors(self):
        scale = self.scene.blocksize
        scene = self.scene
        self.actor_positions = {}
        for actor in self.all_actors:
            self.actor_positions[actor.pos] = actor
            if not self.position_on_screen(actor.pos):
                continue
            if not actor.image:
                continue
            x, y = actor.pos
            x -= self.scene.left
            y -= self.scene.top
            self.screen.blit(actor.image, (x * scale, y * scale))
            self.dirty_tiles[x, y] = True

    def __getitem__(self, pos):
        """
        Position is relative to the scene
        """
        if pos in self.actor_positions:
            return self.actor_positions[pos]
        return self.scene[pos]

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
    # FIXME: this should be relative to the module where this class was imported:
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


    def set_controller(self, controller):
        # Called when scene is first passed to a controller object
        self.controller = controller
        self.load()
        self.tiles = {}
        self.background_plane = {}

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
            self.actor_plane = pygame.image.load(
                self.scene_path_prefix + self.scene_name + self.actor_plane_sufix + ".png")
        except (pygame.error, IOError):
            self.actor_plane = pygame.surface.Surface((1, 1))
            logger.error("Could not find character plane for scene {}".format(self.scene_name))
        self.palette = Palette(self.scene_path_prefix + self.mapdescription)
        self.width, self.height = self.image.get_size()

    def __getitem__(self, position):
        if position in self.background_plane:
            # Self.objects contain static scene objects that may have attributes
            # (such as hardness) - animated game Characters should derive
            # from "Actor", and are "over" the scene: they are retrievable by
            # "Secene.get_actor_at"
            return self.background_plane[position]
        try:
            color = self.image.get_at(position)
        except IndexError:
            return self.out_of_map
        # TODO: load scene block images
        try:
            name = self.palette[color]
        except KeyError:
            self.background_plane[position] = color
            return color
        if name in self.tiles:
            if isinstance(self.tiles[name], type):
                return self.tiles[name](self.controller, position)
            else:
                return self.tiles[name]

        if name.lower() in GameObjectClasses:
            self.tiles[name] = GameObjectClasses[name.lower()]
            return self.tiles[name](self.controller, position)
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
        return GameObjectClasses.get(name, None)

    def move(self, direction):
        self.target_left += direction[0]
        self.target_top += direction[1]

    def clamp_target_location(self):
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
        self.clamp_target_location()

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

class Event(object):
    def __init__(self, countdown, attribute, value):
        self.countdown = countdown
        self.attribute = attribute
        self.value = value

    def __hash__(self):
        return hash(self.attribute)


class GameObject(Sprite):
    __metaclass__ = GameObjectRegistry

    hardness = 0
    def __init__(self, controller, pos=(0,0)):
        self.controller = controller
        self.pos = pos

        self.load_image()
        self.events = set()
        self.tick = 0
        super(GameObject, self).__init__()
        self.update()

    def load_image(self):
        controller = self.controller
        # TODO: allow for more sofisticated image loading
        self.image_path = controller.scene.scene_path_prefix + self.__class__.__name__.lower() + ".png"
        img = pygame.image.load(self.image_path)
        if controller.scene.blocksize != img.get_width():
            ratio = float(controller.scene.blocksize) / img.get_width()
            img = pygame.transform.rotozoom(img, 0, ratio)
        self.base_image = img
        self.image = img

    def update(self):
        super(GameObject, self).update()
        self.process_events()
        bl = self.controller.scene.blocksize
        # location rectangle, in pixels, relative to the scene (not the screen)
        self.rect = pygame.Rect([self.pos[0] * bl, self.pos[1] * bl, bl, bl])
        self.tick += 1

    def process_events(self):
        for  event in list(self.events):
            if event.countdown != 0:
                event.countdown -= 1
                continue
            if callable(event.value):
                event.value(self)
            else:
                setattr(self, event.attribute, event.value)
            self.events.remove(event)

    def on_over(self, other):
        """
        Override this to create a behavior when object is touched by another one
        """
        pass

    def on_touch(self, other):
        """
        Called when an actor touches this object
        """
        pass

class Actor(GameObject):

    strength = 4
    base_move_rate = 4
    blinking = False

    def __init__(self, *args, **kw):
        # self.pos = kw.pop("pos", (0,0))
        self.move_counter = 0

        super(Actor, self).__init__(*args, **kw)

    def move(self, direction):
        if self.move_counter < self.base_move_rate:
            return
        # TODO: implement a simple class for vector algebra like this
        x, y = self.pos
        x += direction[0]
        y += direction[1]
        if isinstance(self.controller[x, y] , GameObject):
            self.controller[x,y].on_touch(self)
        if getattr(self.controller[x, y], "hardness", 0) > self.strength:
            return
        self.pos = x, y
        self.move_counter = 0

    def update(self):
        if self.blinking and self.tick % 2:
            self.image = None
        else:
            self.image = self.base_image
        super(Actor, self).update()
        self.move_counter += 1


class FallingActor(Actor):
    """
    Use this class for side-view games, where things "fall" if there is no ground bellow them
    """
    weight = 1
    gravity = (0, 1)

    def update(self):
        super(FallingActor, self).update()
        if getattr(self.controller[self.pos[0] + self.gravity[0], self.pos[1] + self.gravity[1]], "hardness", 0) < self.weight:
            self.move(self.gravity)
            # if self.pos > self.controller.scene.height:
            #    self.kill()


def simpleloop(scene, size, godmode=False):
    cont = Controller(size, scene)
    try:
        while True:
            frame_start = pygame.time.get_ticks()
            pygame.event.pump()
            cont.update()
            cont.draw()
            pygame.display.flip()
            delay = max(0, FRAME_DELAY - (pygame.time.get_ticks() - frame_start))
            pygame.time.delay(delay)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                raise GameOver
            for direction_name in "RIGHT LEFT UP DOWN".split():
                if keys[getattr(pygame, "K_" + direction_name)]:
                    direction = getattr(Directions, direction_name)
                    if godmode:
                        scene.move(direction)
                    else:
                        cont.main_character.sprites()[0].move(direction)

    except GameOver:
        # cont.scene = EndGameScene()
        pass
    finally:
        cont.quit()

####
# From here on, it should be only example and testing code -
# but some refactoring is probably needed
#


class Brick(GameObject):
    hardness = 5


class Wood(GameObject):
    def on_touch(self, other):
        # Example: raise the Hero strength when wood is touched
        other.strength = 6
        other.blinking = True
        other.events.add(Event(5 * FRAME_DELAY, "blinking", False))
        other.events.add(Event(5 * FRAME_DELAY, "strength", 4))


class Hero(Actor):  # Try inheriting from FallingActor for Platform games
    main_character = True

    margin = 2

    def update(self):
        super(Hero, self).update()

        if self.pos[0] <= self.controller.scene.left + self.margin:
            self.controller.scene.target_left = self.pos[0] - self.margin
        elif self.pos[0] > (self.controller.scene.left + self.controller.blocks_x - self.margin - 1):
            self.controller.scene.target_left = self.pos[0] - self.controller.blocks_x + self.margin + 1

        if self.pos[1] <= self.controller.scene.top + self.margin:
            self.controller.scene.target_top = self.pos[1] - self.margin
        elif (self.pos[1] > self.controller.scene.top + self.controller.blocks_y - self.margin - 1):
            self.controller.scene.target_top = self.pos[1] - self.controller.blocks_y + self.margin + 1



class Animal0(Actor):
    locals().update(Directions.__dict__)
    pattern = [RIGHT, RIGHT, RIGHT, PAUSE, LEFT, LEFT, LEFT, PAUSE]
    move_rate = 12

    def update(self):
        if not self.tick % self.move_rate:
            self.move(self.pattern[(self.tick // self.move_rate) % len(self.pattern)  ])
        super(Animal0, self).update()

    def on_touch(self, other):
        if isinstance(other, Hero):
            other.blinking = True
            other.strength = 6
            other.events.add(Event(5 * FRAME_DELAY, "blinking", False))
            other.events.add(Event(5 * FRAME_DELAY, "strength", 4))
            self.kill()

def main(godmode):
    scene = Scene('scene0')
    simpleloop(scene, SIZE)


if __name__ == "__main__":
    import sys
    godmode = (sys.argv[1] == "--godmode") if len(sys.argv) >= 2 else False
    if godmode:
        del Hero.update
    main(godmode)

