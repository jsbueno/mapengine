# coding: utf-8

class BaseGameException(Exception):
    pass

class GameOver(BaseGameException):
    pass

class CutExit(BaseGameException):
    pass