
from mapengine import Scene, simpleloop, MainActor, Actor, GameObject
from mapengine.base import FallingActor


class SimpleActor(MainActor): #, FallingActor):
    image_sequence = "dude.png", 330
    pass

class Wall(GameObject):
    hardness=10

class Ground(GameObject):
    hardness=5

def main():
    scene = Scene("room")
    simpleloop(scene, (800, 600), godmode=False)

main()


