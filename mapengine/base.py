# coding: utf-8
import pygame

from pygame.color import Color

SIZE = 800, 600


class Directions(object):
    # TODO: create some simple const type with a nice REPR
    RIGHT, LEFT, UP, DOWN = (1, 0), (-1, 0), (0, -1), (0, 1)


class GameOver(Exception):
    pass


class Controller(object):
    def __init__(self, size, scene=None, **kw):
        self.width, self.height = self.size = size
        self.screen = pygame.display.set_mode(size, **kw)
        self.scene = scene

    def update(self):
        self.scene.update()
        self.draw()

    def draw(self):
        self.background()

    def background(self):
        scene = self.scene
        scale = scene.blocksize
        blocks_x = self.width // scale
        blocks_y = self.width // scale
        for x in range(blocks_x):
            for y in range(blocks_y):
                image = scene[x + scene.left, y + scene.top]
                if isinstance(image, Color):
                    pygame.draw.rect(self.screen, image, (x * scale, y * scale, scale, scale))
                else:  # image
                    self.screen.blit(image, (x * scale, y * scale))

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

    """

    def __init__(self, scene_name, **kw):
        # FIXME: allow different extensions, attempt to file-name case sensitiveness
        self.mapfile = scene_name + ".png"
        self.mapdescription = scene_name + ".gpl"
        self.load()
        self.tiles = {}

        # TODO: factor this out to a mixin "autoattr" class
        for line in self.attributes.split("\n"):
            line = line.strip("\x20\x09,")
            if not line or line[0].startswith("#"):
                continue
            attr, value = line.split(None, 1)
            self.load_attr(attr, value, kw)

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


CharacterClasses = {}
class CharacterRegistry(type):
    def  __new__(metacls, name, bases, dct):
        cls = type.__new__(metacls, name, bases, dct)
        CharacterClasses[name] = cls
        return cls


class Character(pygame.sprite.Sprite):
    __metaclass__ = CharacterRegistry
    def __init__(self):
        super(Character, self).__init__()


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

