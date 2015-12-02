# coding: utf-8

from .exceptions import CutExit

from .fonts import FontLoader

import pygame
from pygame.locals import *

delay = 350
class Cut(object):
    title_font = "sans.ttf", 64
    option_font = "sans.ttf", 32
    controller = None
    def __init__(self, title, options=(), exit=None, **kw):
        self.title = title
        self.options = options
        self.exit = exit
        # each option is a tuple with the text to be displayed
        # and a callable action to be taken when it is selected.
        # (the callable action is passed the controller as the sole parameter,
        # and may act on the controller or raise an appropriate exception)
        # if no option is given, the "cut" finishes with a raise CutExit
        # on fire, esc or mouse button being pressed.

        # In Progress: for now, there is no proper menu widget, and options
        # are displayed prefixed with a single numeric choice.

        self.background = kw.get("background", (0, 0, 0))
        self.kwargs = kw

    def __call__(self, controller):
        self.current_title_font = FontLoader(*self.title_font)
        self.current_options_font = FontLoader(*self.title_font)
        self.rendered_title = None
        self.rendered_options = []
        self.controller = controller
        return self

    def update(self):
        screen = self.controller.screen
        screenparts = len(self.options) + 2
        y_step = screen.get_height() // screenparts

        # TODO: Use font animation library (factor out from gedigi-pygame)
        if not self.rendered_title:
            self.rendered_title = self.current_title_font.render(self.title)
            for i, option in enumerate(self.options, 1):
                self.rendered_options.append(self.current_options_font.render(self.options[0]))

            # WIP: for now, cuts are static text - so no need to re-render at each frame
            if isinstance(self.background, pygame.Surface):
                screen.blit(self.background, (0,0))
            else:
                screen.fill(self.background)
            offset_x = (screen.get_width() - self.rendered_title.get_width()) // 2
            offset_y = y_step - self.rendered_title.get_height() // 2
            screen.blit(self.rendered_title, (offset_x, offset_y))
            for r_option, offset_y in zip(self.rendered_options, range(y_step * 2, screen.get_height(), y_step)):
                offset_x = (screen.get_width() - r_option.get_width()) // 2
                offset_y = offset_y - r_option.get_height() // 2
                screen.blit(r_option, (offset_x, offset_y))
        pygame.display.flip()

        pygame.event.pump()
        keys = pygame.key.get_pressed()
        if not self.options and (keys[K_SPACE] or keys[K_RETURN] or keys[K_ESCAPE]):
            if self.exit:
                self.exit(self.controller)
            else:
                raise CutExit
        for i, option in enumerate(self.options, 1):
            # <esc> also triggers the first option
            if keys[str(i)] or keys[K_ESCAPE]:
                option[1](self.controller)
                # a pause to allow for menu navigation - 
                # (the callable could change our options)
                pygame.time.delay(350)
                break

