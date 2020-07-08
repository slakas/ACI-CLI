#!/usr/bin/env python
# -*- encoding: utf-8 -*-
################################################################################
#
# Klasa obsułgująca tryb debbuging
#
################################################################################



class Debuger:

    def __init__(self, level=0):
        self.lvl = level

    def print_to_screen(self, line, msg = ''):
        print("%%% Linia {nr} %%% {msg}".format(nr=line, msg=msg))
