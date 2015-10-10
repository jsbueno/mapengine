# coding: utf-8
import pygame


class GameOver(Exception):
    pass


class Controller(object):
    def __init__(self, SIZE, scene=None, **kw):
        self.screen = pygame.display.set_mode(SIZE, **kw)
        self.scene = scene

    def update(self):
        self.scene.update()

    def quit():
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
        self.load()

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.color_names[key]
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
            for line in file_:
                line = line.strip()
                if len(line.split()) < 4 or line.startswith('#'):
                    continue
                r, g, b, name = line.strip().split(None, 4)
                color = pygame.color.Color(int(component) for component in (r, g, b))
                self.colors[color] = name
                self.color_names[name] = color


class Scene(object):
    mapfile = "scene0.png"
    mapdescription = "scene0.gpl"
    mapscale = 32

    def __init__(self):
        self.X = 0
        self.Y = 0

    def update(self):
        pass


def main():
    cont = Controller
    try:
        while True:
            cont.update()
            cont.draw()
            pygame.display.flip()
            pygame.time.delay(30)

    except GameOver:
        # cont.scene = EndGameScene()
        pass
    finally:
        cont.quit()


if __name__ == "__main__":
    main()

