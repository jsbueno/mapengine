# coding: utf-8

import sys
from mapengine import base
from mapengine import Scene, simpleloop


godmode = (sys.argv[1] == "--godmode") if len(sys.argv) >= 2 else False
if godmode:
    del base.Hero.update

def main(godmode):
    scene = Scene('scene0')
    simpleloop(scene, base.SIZE)

main(godmode)