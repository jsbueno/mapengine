# coding: utf-8

from copy import copy
from functools import partial
import logging
import os
import random
import textwrap
import sys

import pygame

from pygame.color import Color
from pygame.sprite import Sprite, Group

from .utils import resource_load, pwd, Vector, V
from .palette import Palette
from .fonts import FontLoader
from .cut import Cut
from .global_states import SCENE_PATH
from .exceptions import GameOver, CutExit, RestartGame, SoftReset, Reset

SIZE = 800, 600
FRAME_DELAY = 30


logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, os.environ.get("LOGLEVEL", "INFO")))

try:
    range = xrange
except NameError:
    pass

class CDirections(object):
    # TODO: create some simple const type with a nice REPR
    RIGHT, LEFT, UP, DOWN = V((1, 0)), V((-1, 0)), V((0, -1)), V((0, 1))
    def __getitem__(self, d):
        if d == self.RIGHT:
            v = "right"
        elif d == self.LEFT:
            v = "left"
        elif d == self.UP:
            v = "up"
        elif d == self.DOWN:
            v = "down"
        else:
            raise IndexError
        return v

Directions = CDirections()

PAUSE = V((0,0))

def add_scene_path(path):
    """
    Use this to explicitly add a directory to the
    scene loading machinism.
    If you don't add a path explictly, mapengine tries to guess
    a "scenes/" directory from your working dir. But
    the mechanisms for it may not work that well.
    """
    SCENE_PATH.append(path)


class Controller(object):
    def __init__(self, size, scene=None, **kw):
        pygame.init()
        self.width, self.height = self.size = size
        self.screen = pygame.display.set_mode(size, **kw)

        try:
            self.hard_reset()
        except Reset:
            pass
        self.load_scene(scene)

    def hard_reset(self):
        # This dict is where the game should keep
        # character and story data that persist across phaes,
        # like lifes, energy, inventory, encounters that happened, etc:

        self.inside_cut = False
        self.diary = {}
        return self.soft_reset()

    def soft_reset(self, raise_=True):
        self.actor_positions = {}
        self.old_top = -20
        self.old_left = -20
        self.old_tiles = {}
        self.dirty_tiles = {}
        self.force_redraw = False
        self.post_cut_action = None
        if raise_:
            raise SoftReset

    def load_scene(self, scene, skip_post_cut=False, skip_pre_cut=False):
        if getattr(self, "scene", None) and self.scene.post_cut and not skip_post_cut:
            post_cut_action = partial(self.load_scene, scene, skip_post_cut=True, skip_pre_cut=skip_pre_cut)
            return self.enter_cut(self.scene.post_cut, post_cut_action)

        self.scene = scene
        scene.set_controller(self)
        self.all_actors = Group()
        self.actors = {}
        self.load_initial_actors()
        self.messages = Group()
        if self.scene.pre_cut and not skip_pre_cut:
            return self.enter_cut(self.scene.pre_cut)

    def enter_cut(self, cut, post_action=None):
        self.post_cut_action = post_action
        self.inside_cut = True
        self.current_cut = cut(self)
        return self.update()

    def leave_cut(self):
        self.inside_cut = False
        if self.post_cut_action:
            action = self.post_cut_action
            self.post_cut_action = None
            action()

    def draw_cut(self):
        self.current_cut.update()

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

    @property
    def protagonist(self):
        sprites = self.main_character.sprites()

        return sprites[0] if sprites else None

    @staticmethod
    def _touch(actor1, actor2):
        if actor1 is actor2:
            return False
        return actor1.rect.colliderect(actor2.rect)

    def update(self):
        if self.inside_cut:
            try:
                return self.draw_cut()
            except CutExit:
                self.leave_cut()
        try:
            self.scene.update()
            for actor in self.all_actors:
                if actor.off_screen_update or self.is_position_on_screen(actor.pos):
                    actor.update()
                for collision in pygame.sprite.spritecollide(actor, self.all_actors, False, collided=self._touch):
                    actor.on_over(collision)
                if isinstance(self.scene[actor.pos], GameObject):
                    self.scene[actor.pos].on_over(actor)
            self.draw()
        except SoftReset:
            pass


    def draw(self):
        self.background()
        self.draw_actors()
        self.display_messages()

    scale = property(lambda self: self.scene.blocksize)
    # These hold the on-screen size of the game-scene in blocks
    blocks_x = property(lambda self: self.width // self.scale)
    blocks_y = property(lambda self: self.height // self.scale)

    def iter_blocks(self):
        for x in range(self.blocks_x):
            for y in range(self.blocks_y):
                yield x, y

    def background(self):
        if self.scene.overlay_image:
            self.overlay_background()
        else:
            self.block_background()
        self.old_left = self.scene.left
        self.old_top = self.scene.top
        self.force_redraw = False

    def block_background(self):
        scene = self.scene
        scale = self.scale
        for x, y in self.iter_blocks():
            obj = scene[x + scene.left, y + scene.top]
            image = obj.image if hasattr(obj, "image") else obj
            self._draw_tile_at((x,y), image, self.force_redraw)

    def _draw_tile_at(self, pos, image, force=False):
        x, y = pos
        scale = self.scale
        if not force and self.old_tiles.get(pos, None) is image and not self.dirty_tiles.get(pos, False):
            return
        if isinstance(image, Color):
            pygame.draw.rect(self.screen, image, (x * scale, y * scale, scale, scale))
        else:  # image
            self.screen.blit(image, (x * scale, y * scale))
        self.old_tiles[pos] = image
        self.dirty_tiles.pop(pos, False)

    def overlay_background(self):
        scene = self.scene
        if not self.force_redraw and self.old_left == scene.left and self.old_top == scene.top:
            return self._draw_overlay_tiles()
        pixel_left = scene.left * scene.blocksize
        pixel_top = scene.top * scene.blocksize
        self.screen.blit(scene.overlay_image, (0, 0), area=(pixel_left, pixel_top, self.width, self.height))

    def _draw_overlay_tiles(self):
        scene = self.scene
        blocksize = scene.blocksize
        for pos, dirty in list(self.dirty_tiles.items()):
            if not dirty:
                continue
            pixel_left = (scene.left + pos[0]) * blocksize
            pixel_top = (scene.top + pos[1]) * blocksize
            local_left = blocksize * pos[0]
            local_top = blocksize * pos[1]
            self.screen.blit(scene.overlay_image, (local_left, local_top),
                             area=(pixel_left, pixel_top, blocksize, blocksize))
            self.dirty_tiles.pop(pos)

    def is_position_on_screen(self, pos):
        return (self.scene.left <= pos[0] < self.scene.left + self.blocks_x and
                self.scene.top <= pos[1] < self.scene.top + self.blocks_y)

    def to_screen(self, pos):
        return V((pos[0] - self.scene.left, pos[1] - self.scene.top))

    def draw_actors(self):
        scale = self.scene.blocksize
        scene = self.scene
        self.actor_positions = {}
        for actor in self.all_actors:
            self.actor_positions[actor.pos] = actor
            if not self.is_position_on_screen(actor.pos):
                continue
            if not actor.image:
                continue
            x, y = pos = self.to_screen(actor.pos)
            if actor.speed:
                # import ipdb; ipdb.set_trace()
                old_pos = self.to_screen(actor.old_pos)
                ipos = old_pos + (pos - old_pos) * actor.speed * min((actor.tick - actor.move_direction_count), actor.base_move_rate)
                x, y = ipos
                self.dirty_tiles[old_pos] = True
                self.dirty_tiles[pos] = True
                self.dirty_tiles[V((old_pos.x, pos.y))] = True
                self.dirty_tiles[V((pos.x, old_pos.y))] = True
            else:
                self.dirty_tiles[pos] = True
            self.screen.blit(actor.image, (x * scale, y * scale))

    def display_messages(self):
        scale = self.scene.blocksize
        for message in self.messages:
            if not self.is_position_on_screen(message.owner.pos):
                continue
            image = message.render()
            # Initially all message swill pop bellow the actors, at half-block-lenght to left
            # TODO: enhance message block display heuristics

            position = self.to_screen(message.owner.pos)
            x = position[0] + 0.5
            y = position[1] + 1
            self.screen.blit(image, (int(x * scale), y * scale))
            for j in range(0, (image.get_width() // scale) + 2):
                for k in range(0, (image.get_height() // scale) + 1):
                    self.dirty_tiles[int(x) + j, y + k] = True

    def __getitem__(self, pos):
        """
        Position is relative to the scene
        """
        if pos in self.actor_positions:
            return self.actor_positions[pos]
        return self.scene[pos]

    def quit(self):
        pygame.quit()


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

    display_type block   # allowed values: 'block' and 'overlay'
                         # 'overlay' will load a <name>_overlay.png file that will be 
                         # displayed as game background instead of block tiles

    scroll_rate 8

    out_of_map self.out_of_map
    actor_plane_sufix _actors
    overlay_plane_sufix _overlay

    pre_cut None
    post_cut None


    game_over_cut None
    music None
    """

    def __init__(self, scene_name, **kw):
        # FIXME: allow different extensions, attempt to file-name case sensitiveness
        self.scene_name = scene_name
        self.mapfile = scene_name
        self.mapdescription = scene_name + ".gpl"
        self.overlay_image = None

        self.cached_images = {}

        # TODO: factor this out to a mixin "autoattr" class
        for line in self.attributes.split("\n"):
            line = line.strip("\x20\x09,")
            if not line or line[0].startswith("#"):
                continue
            attr, value = line.split(None, 1)
            value = value.split("#")[0].strip()
            self.load_attr(attr, value, kw)

        if self.music is None:
            self.music = scene_name + ".ogg"

        if self.game_over_cut is None:
            self.game_over_cut = Cut("Game Over", options=[
                ("Start new game", self.default_game_over_continue),
                ("Exit", self.default_game_over_exit),
            ])
        SCENE_PATH.append(os.path.join(pwd(2), self.scene_path_prefix))

    @staticmethod
    def default_game_over_exit(controller):
        raise GameOver

    @staticmethod
    def default_game_over_continue(controller):
        raise RestartGame

    def set_controller(self, controller):
        # Called when scene is first passed to a controller object
        self.controller = controller
        if not self.display_size:
            self.display_size = SIZE
        self.load()
        self.tiles = {}
        self.background_plane = {}

        self.scroll_count = 0
        self.music_load(self.music)
        self.start_music()

    def load_attr(self, attrname, default, kw):
        if isinstance(default, str):
            if default.isdigit():
                default = int(default)
            elif default.startswith("self."):
                default = getattr(self, default[len("self."):])
            elif default == "None":
                default = None
        setattr(self, attrname, kw.get(attrname, default))

    def image_load(self, filename=None, sufix="", **kw):
        if not filename:
            filename = self.mapfile
        if not filename.lower().endswith((".png", ".bmp", ".tif", ".tiff")):
            filename += sufix + ".png"
        return resource_load(filename, paths=SCENE_PATH, cache=self.cached_images, loader=pygame.image.load, **kw)

    def start_music(self):
        if getattr(self, "music_path", None):
            self.playing = pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.play(-1)

    def music_load(self, filename):
        resource_load(filename, paths=SCENE_PATH, loader=lambda path: setattr(self, "music_path", path))

    def load(self):
        self.image = self.image_load(force=True)
        empty_plane = pygame.surface.Surface((1, 1))
        self.actor_plane = self.image_load(sufix=self.actor_plane_sufix, default=empty_plane)
        if self.actor_plane is empty_plane:
            logger.error("Could not find character plane for scene {}".format(self.scene_name))
        self.palette = resource_load(self.mapdescription, paths=SCENE_PATH, loader=Palette)
        #Palette(self.mapdescription)
        self.width, self.height = self.image.get_size()

        # Scene blocksize in pixels:
        self.blocksize = self.display_size[0] // self.window_width

        if self.display_type == "overlay":
            try:
                overlay_image = self.image_load(sufix=self.overlay_plane_sufix)
                ratio =  float(self.width * self.blocksize) / overlay_image.get_width()
                # TODO: this image can become too large for big maps
                # make use of a lazy-zooming mechanism to scale the overlay to full-size
                # only on the displayed area.
                self.overlay_image = pygame.transform.rotozoom(overlay_image, 0, ratio)
            except (pygame.error, IOError):
                logger.error("Could not load overlay image '{}.png'".format(self.mapfile + self.overlay_plane_sufix))


    def __getitem__(self, position):
        if not position in self.background_plane:
            self.background_plane[position] = self._raw_getitem(position)
            # Self.objects contain static scene objects that may have attributes
            # (such as hardness) - animated game Characters should derive
            # from "Actor", and are "over" the scene: they are retrievable by
            # "Scene.get_actor_at"
        return self.background_plane[position]

    def _raw_getitem(self, position):
        try:
            color = self.image.get_at(position)
        except IndexError:
            return self.out_of_map
        try:
            name = self.palette[color]
        except KeyError:
            return color
        if name in self.tiles:
            if isinstance(self.tiles[name], type):
                return self.tiles[name](self.controller, position)
            else:
                return self.tiles[name]
        if name.lower() in GameObjectClasses:
            self.tiles[name] = GameObjectClasses[name.lower()]
            return self.tiles[name](self.controller, position)

        img = self.image_load(name)
        if img is None:
            self.tiles[name] = color
        else:
            if img.get_width() != self.blocksize:
                ratio = float(self.blocksize) / img.get_width()
                img = pygame.transform.rotozoom(img, 0, ratio)
            self.tiles[name] = img
        return self.tiles[name]

    def __delitem__(self, position):
        del self.background_plane[position]

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

TEXT_WIDTH = 20

class Blob(Sprite, FontLoader):
    """
    On screen text message blob
    """

    def __init__(self, message, owner, width=TEXT_WIDTH, timeout=None, *args, **kw):

        self.timeout = timeout

        self.width = width
        self.owner = owner

        self.margin = kw.get("margin", 30)
        self.frame = kw.get("frame", 3) # 0 or None for no frame
        self.background = kw.get("background", (0, 0, 0, 172))
        self.antialias = kw.get("antialias", True)
        self.line_spacing = kw.get("line_spacing", 2)
        self.justification = kw.get("justification", "left") # left, right, center
        self.kwargs = kw
        self.message = self.text_lines = message
        self.owner = owner
        self.rendered_message = None

        # Pygame's Sprite can't graciously handle a "super" call. 
        # So we call both superclasses' __init__
        FontLoader.__init__(self, *args, **kw)
        Sprite.__init__(self)

    def render(self):
        if self.rendered_message == self.message:
            return self.image
        max_width = 0
        total_height = 0
        rendered_lines = []
        for line in textwrap.wrap(self.message, self.width):
            rendered_line = self.font.render(line, self.antialias, self.color)
            rendered_lines.append(rendered_line)
            max_width = max(max_width, rendered_line.get_width())
            total_height += rendered_line.get_height() + self.line_spacing
        image = pygame.Surface((max_width + 2 * self.margin, total_height + 2 * self.margin))
        image.fill(self.background)
        v_offset = self.margin
        for line in rendered_lines:
            if self.justification == "left":
                h_pos = self.margin
            elif self.justification == "right":
                h_pos = image.get_width() - self.margin - line.get_width()
            else: # center
                h_pos = (image.get_width() - line.get_width()) // 2
            image.blit(line, (h_pos, v_offset))
            v_offset += line.get_height() + self.line_spacing

        if self.frame:
            pygame.draw.rect(
                image, self.color, (
                    self.margin // 2, self.margin // 2,
                    max_width + self.margin,
                    total_height + self.margin
                ),
                self.frame
            )

        self.image = image
        self.rendered_message = self.message
        return image

    def kill(self):
        self.owner.controller.force_redraw = True
        super(Blob, self).kill()


class GameObject(Sprite, metaclass=GameObjectRegistry):

    hardness = 0
    background_image = None
    image_sequence = None # Image sequence can be a tuple of filename + sprite_width. 
                          # the file is loaded and cut in squarres of sprite_width pixels - 
                          # with up to 3 rows. First row is mirrored left/right
                          # following rows are used for up/down. First sprite
                          # in each row is used for stopped character - others
                          # are used by character when in movement
    image_name = None
    image_cache = {}
    base_image = image = None
    auto_flip = False
    off_screen_update = False

    def __init__(self, controller, pos=(0,0)):
        self.messages = Group()
        self.controller = controller
        self.old_pos = self.pos = V(pos)
        self.images = {}
        if not self.image_sequence:
            self.image_load(self.image_name or self.__class__.__name__.lower())
        else:
            self.auto_image_sequence_load(self.image_sequence)
        self.events = set()
        self.tick = 0
        super(GameObject, self).__init__()
        self.move_direction = Directions.RIGHT
        self.move_direction_count = 0
        self.speed = 0
        self.showing_text = False
        self.message_queue = []
        self.update()

    def _resize(self, img):
        img_size = self.controller.scene.blocksize
        ratio = float(img_size) / max(img.get_size())
        img = pygame.transform.rotozoom(img, 0, ratio)
        return img

    def raw_image_load(self, name, resize=True):
        scene = self.controller.scene
        img_size = scene.blocksize
        img = scene.image_load(name)
        if not img:
            color = scene.palette[self.__class__.__name__]
            img = pygame.Surface((img_size, img_size), pygame.SRCALPHA)
            img.fill(color)
        if resize and img_size != max(img.get_size()):
            img = self._resize(img)
        return img

    def image_load(self, name):
        self.base_image = img = self.raw_image_load(name)
        if self.auto_flip:
            self.images["up"] = self.images["right"] = [img]
            self.images["down"] = self.images["left"] = [pygame.transform.flip(img, True, False)]
        if self.background_image:
            img = self.raw_image_load(self.background_image)
            img.blit(self.base_image, (0,0))
        self.image = img

    def image_sequence_load(self, image_sequence, resize=True):
        if image_sequence in self.__class__.image_cache:
            return self.__class__.image_cache[image_sequence]
        filename = image_sequence[0]
        img = self.raw_image_load(filename, resize=False)
        width = image_sequence[1]
        height = image_sequence[2] if len(image_sequence) > 2 else img.get_height()

        imgs = []
        for offset_y in range(0, img.get_height(), height):
            strip = []
            for offset_x in range(0, img.get_width(), width):
                new_img = pygame.Surface((width, height), pygame.SRCALPHA)
                new_img.blit(img, (0, 0), (offset_x, offset_y, width, height))
                if resize:
                    new_img = self._resize(new_img)
                strip.append(new_img)
            imgs.append(strip)
        self.__class__.image_cache[image_sequence] = imgs
        return imgs


    def auto_image_sequence_load(self, file_sequence, name=""):
        """ Load several images as animation sequences. 
        The format of the "image_sequence" attribute is a work in progress:
        you can pass a sequence of an image-file name followed by one or two numbers, meaning
        the width [and height] of each sprite on the image. 
        From one set of images, images will be created for characters facing left or right - 
        for two given sets: the first set is used for left, right and down, and the second for up.
        with three sets: left, and right, then up, then down

        Called automatically if the class "image_sequence" is set.

        The given file_sequence is stored in self.images[<key>]  where <key> is 
        <right/left/up/down>[_name]
        (ex. "right_jump")
        """
        if 2 <= len(file_sequence) <= 3 and isinstance(file_sequence[0], str):
            file_sequence = [file_sequence]
        sequences = []
        for part in file_sequence:
            sequences.extend(self.image_sequence_load(tuple(part)))
        key_base = "{{}}_{}".format(name) if name else "{}"
        right_images = self.images[key_base.format("right")] = sequences[0]
        left_images = self.images[key_base.format("left")] = [pygame.transform.flip(img, True, False) for img in sequences[0]]

        self.images[key_base.format("up")] = sequences[1] if len(sequences) > 1 else right_images
        self.images[key_base.format("down")] = sequences[2] if len(sequences) > 2 else left_images


    def update(self):
        self.process_events()
        bl = self.controller.scene.blocksize
        # location rectangle, in pixels, relative to the scene (not the screen)
        self.rect = pygame.Rect([self.pos[0] * bl, self.pos[1] * bl, bl, bl])
        self.tick += 1
        if self.images:
            try:
                direction_str = Directions[self.move_direction]
            except IndexError:
                return super(GameObject, self).update()
            moving_time = self.tick - self.move_direction_count
            if moving_time > 1.5 * self.base_move_rate:
               self.speed = 0
            if not self.speed or len(self.images[direction_str]) == 1:
                self.base_image = self.images[direction_str][0]
            else:
                index =  (moving_time  // self.base_move_rate) % (len(self.images[direction_str]) - 1)
                self.base_image = self.images[direction_str][1 + index]
            # For now, the reason to have "image" and "base_image" is the blinking attribute
            self.image = self.base_image
        if self.message_queue:
            self.show_text()
        return super(GameObject, self).update()

    def process_events(self):
        for event in list(self.events):
            if event.countdown >= 0:
                event.countdown -= 1
                continue
            if callable(event.attribute):
                if event.value is None:
                    args = []
                elif not isinstance(event.value, list):
                    args = [event.value]
                event.attribute(*args)
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

    def on_fire(self):
        for message in self.controller.messages:
            message.kill()
            message.owner.showing_text= False
        
    def show_text(self, message="", duration=None, **kw):
        if not self.showing_text:
            if not message:
                message, duration, kw = self.message_queue.pop(0)
            message_blob = Blob(message, self, **kw)
            message_blob.owner = self
            self.controller.messages.add(message_blob)
            self.current_message = message_blob
            self.messages.add(message_blob)
            self.showing_text = True
            if duration:
                self.events.add(Event(duration * FRAME_DELAY, message_blob.kill, None))
                self.events.add(Event(duration * FRAME_DELAY, "showing_text", False))
        else:
            self.message_queue.append((message, duration , kw))
        

    def kill(self):
        for message in self.messages:
            message.kill()
        return super(GameObject, self).kill()


class Actor(GameObject):

    strength = 4
    base_move_rate = 4
    blinking = False
    auto_flip = True

    def __init__(self, *args, **kw):
        # self.pos = kw.pop("pos", (0,0))
        self.move_counter = 0

        super(Actor, self).__init__(*args, **kw)

    def move(self, direction):
        if self.move_counter < self.base_move_rate:
            return
        self.old_pos = self.pos
        new_pos = self.pos + direction
        scene = self.controller.scene
        if new_pos.x < 0 or new_pos.x > scene.width or new_pos.y < 0 or new_pos.y > scene.height:
            return
        self.move_direction = direction
        self.move_direction_count = self.tick
        self.speed = 1.0 / self.base_move_rate 
        other_obj = self.controller[new_pos]
        if isinstance(other_obj , GameObject):
            self.controller[new_pos].on_touch(self)
        if getattr(other_obj, "hardness", 0) > self.strength:
            return
        self.pos = new_pos
        self.move_counter = 0

    def update(self):
        super(Actor, self).update()
        if self.blinking and self.tick % 2:
            self.image = None
        else:
            self.image = self.base_image
        self.move_counter += 1

    def on_fire(self):
        """"
        Called if this is the main character and the fire key
        (usually <space>) has been pressed.
        """
        super(Actor, self).on_fire()


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
    controller = Controller(size, scene)

    try:
        controller = Controller(size, scene)
        continue_ = True
        while continue_:
            try:
                while True:
                    frame_start = pygame.time.get_ticks()
                    pygame.event.pump()
                    controller.update()
                    if controller.inside_cut:
                        continue
                    pygame.display.flip()
                    delay = max(0, FRAME_DELAY - (pygame.time.get_ticks() - frame_start))
                    pygame.time.delay(delay)

                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_ESCAPE]:
                        raise GameOver
                    main_character = (controller.protagonist) if not godmode else None
                    for direction_name in "RIGHT LEFT UP DOWN".split():
                        if keys[getattr(pygame, "K_" + direction_name)]:
                            direction = getattr(Directions, direction_name)
                            if godmode:
                                scene.move(direction)
                            else:
                                main_character.move(direction)
                        if keys[pygame.K_SPACE] and not godmode:
                            main_character.on_fire()


            except GameOver:
                continue_ = False
            except RestartGame:
                scene.top = scene.left = 0
                controller.load_scene(scene)
                try:
                    controller.hard_reset()
                except Reset:
                    pass

    finally:
        controller.quit()

class MainActor(Actor):
    # This attributes defines for the controller the character around which the
    # map is scrolled
    #  (Try inheriting from FallingActor for Platform games)
    main_character = True

    margin = 2

    def update(self):
        super(MainActor, self).update()

        if self.pos[0] <= self.controller.scene.left + self.margin:
            self.controller.scene.target_left = self.pos[0] - self.margin
        elif self.pos[0] > (self.controller.scene.left + self.controller.blocks_x - self.margin - 1):
            self.controller.scene.target_left = self.pos[0] - self.controller.blocks_x + self.margin + 1

        if self.pos[1] <= self.controller.scene.top + self.margin:
            self.controller.scene.target_top = self.pos[1] - self.margin
        elif (self.pos[1] > self.controller.scene.top + self.controller.blocks_y - self.margin - 1):
            self.controller.scene.target_top = self.pos[1] - self.controller.blocks_y + self.margin + 1

    def kill(self):
        super(MainActor, self).kill()
        self.controller.enter_cut(self.controller.scene.game_over_cut)

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


class Hero(MainActor):
    pass


class Animal0(Actor):
    locals().update(CDirections.__dict__)
    pattern = [RIGHT, RIGHT, RIGHT, PAUSE, LEFT, LEFT, LEFT, PAUSE]
    move_rate = 12

    def update(self):
        if not self.tick % self.move_rate:
            self.move(self.pattern[(self.tick // self.move_rate) % len(self.pattern)  ])
        super(Animal0, self).update()

    def on_over(self, other):
        if isinstance(other, Hero):
            other.blinking = True
            other.strength = 6
            other.events.add(Event(10 * FRAME_DELAY, "blinking", False))
            other.events.add(Event(10 * FRAME_DELAY, "strength", 4))
            if not self.messages:
                message = u"Ble" + u"e" * random.randint(1, 3)
                if random.randint(0, 4) == 0:
                    message = u"I should be the killer rabbit of Kaernanog! Bleee! Be afraid!"
                self.show_text(message, duration=2)


class Animal1(Animal0):
    def on_over(self, other):
        if isinstance(other, Hero):
            other.kill()
