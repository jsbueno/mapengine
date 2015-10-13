# coding: utf-8
import pygame

from pygame.color import Color

SIZE = 800, 600

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
        scale = scene.mapscale
        blocks_x = self.width / scale
        blocks_y = self.width / scale
        for x in range(blocks_x):
            for y in range(blocks_y):
                image = scene[x + scene.left,y + scene.top]
                if isinstance(image, Color):
                    pygame.draw.rect(self.screen, image, (x * scale, y * scale, scale, scale))
                else: # image
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
    mapscale = 64
    scene_path_prefix = "scenes/"
    out_of_map = Color(0,0,0)

    def __init__(self, mapfile, mapdescription, **kw):
        self.top = 0
        self.left = 0
        self.mapfile = mapfile
        self.mapdescription = mapdescription
        self.load()

    def load(self):
        self.image = pygame.image.load(self.scene_path_prefix + self.mapfile)
        self.palette = Palette(self.scene_path_prefix + self.mapdescription)

    def __getitem__(self, position):
        try:
            color = self.image.get_at(position)
        except IndexError:
            return self.out_of_map
        # TODO: load scene block images
        return color

    def update(self):
        pass


def main():
    mapfile = "scene0.png"
    mapdescription = "scene0.gpl"
    cont = Controller(SIZE, Scene(mapfile, mapdescription))
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

    except GameOver:
        # cont.scene = EndGameScene()
        pass
    finally:
        cont.quit()


if __name__ == "__main__":
    main()

