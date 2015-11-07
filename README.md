====================================
MAP ENGINE
====================================

This project is to serve as an open framework
for easy creation of complete Python 2D games
that make use of a map and scenario.

The engine defines base classes and utilities that will
allow one to describe a game scene for either a 2D map
game (an Adventure, or 2D shooter top view shooter) or
a side-scrolling game (shot'em up, platformer, side-scrolling shooter)
by drawwing the maps directly ina  pixel-based Image editor (GIMP 2.8 will do),
and implementing sub-class to describe the behavior of the various elements on the scene,
and bind image_map colors to in-game objects.

The initial version uses Pygame, but the plans are to abstract that away
to allow for other 2D multimedia libraries to be used (one wanted
target is Brython + html5 Canvas).

The project is being created as part of the 2015 edition of the
"Jovem Hacker" project in Campinas -http://jovemhacker.org/ -
and to provide a code-base upon which the students can create
their final projects as Python games.

----------------------
Usage
---------------------
The project is fairly incomplete - the idea is for one to extend, or
instantiate with custom parameters the 'Scene' class, and have, before calling
it a scene directory with a PNG file, where the map is saved with <scene_name.png> and
a GIMP Palette (.gpl) file is saved with the <scene_name>.gpl file.  The color names
on the GIMP palette are used to load further png files to draw objects
on the scene, as a map. Check the examples (When those are ready).

(Note: GIMP automatically saves palettes to its palettes' folder - one
have to manually copy the file from, for example, ~/.GIMP/2.0/palettes to
the scenes folder)


-------------
TODO
------------
Main missing things: 
  -  animation support: support for some kind of animation though game sprites
  -  sound support: there is no sound integration whatever
  -  fully working examples for action and RPG game
  -  Smooth movements: this is mostly a ' very nice to have' - currently all objects
  only move one block at a time. It could break things when implemented.
  -  Nice support for opening/game over screens/leather board/between phases splash

Wishlist:

  - Add support for zip and egg files (including the resources, allowing entire games to be distributted as a single file)
  - "super blocks" Game Objetcs comprised by more than one contiguous game block, (displaying a bigger image, and behavinfgg accordingly)