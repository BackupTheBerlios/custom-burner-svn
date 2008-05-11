#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This file is part of:
Custom Burner server
Copyright 2008 Arrigo Marchiori
This program is distributed under the terms of the GNU General Public
License, as specified in the COPYING file.

This file is part of Custom Burner.

Custom Burner is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

Custom Burner is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Custom Burner; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import logging
import curses
import curses.wrapper
from custom_burner import common
import accumulator

class CursesWindowWrapper:
    """This is a wrapper of the curses.Window class.

    We need it because it's not possible
    to have curses.newwin() generate an instance of this class."""

    def __init__(self, height, width, y, x):
        """Constructor (same parameters as curses.newwin()."""
        self.__window = curses.newwin(height, width, y, x)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.__window.refresh()
        self.__firstShownLine = 0;
        self.__data = []
        self.__title = ""

    def getch(self):
        """Proxy for curses.window.getch()"""
        return self.__window.getch()

    def timeout(self, data):
        """Proxy for curses.window.timeout()"""
        return self.__window.timeout(data)

    def __refreshContent(self):
        """Redraws the window from scratch."""
        self.__window.clear()
        self.__window.border()
        self.__window.addstr(0, 1, self.__title)
        for i in range(self.__firstShownLine, len(self.__data) - 1):
            self.__window.addnstr(i - self.__firstShownLine + 1, 1, 
                                 self.__data[i], self.width - 2)
        self.__window.addstr(self.height - 1, self.width - 4, 
                             str(len(self.__data)))

    def scrollUp(self):
        """Scrolls the window content up one line and calls refreshContent()"""
        if self.__firstShownLine < len(self.__data):
            self.__firstShownLine += 1
            self.__refreshContent()
        else:
            curses.beep()

    def addLine(self, line):
        """Adds a line to the end of the window text."""
        self.__data.append(line)
        lines = len(self.__data)
        if self.__firstShownLine == lines - self.height + 2:
            # We need to scroll everything upwards
            self.scrollUp()
        self.__window.addnstr(lines - self.__firstShownLine, 1, line, 
                              self.width - 2)
        self.__window.addstr(self.height - 1, self.width - 4, str(lines))

    def setTitle(self, title):
        """Sets the window title"""
        self.__title = title
        self.__refreshContent()

    def refresh(self):
        return self.__window.refresh()


class IsoWindow(CursesWindowWrapper):
    """A window that displays the list of ISOs."""

    def __init__(self, height, width, y, x):
        CursesWindowWrapper.__init__(self, height, width, y, x)
        self.setTitle("ISO list")


class LogWindow(CursesWindowWrapper):
    """A window that displays log messages."""

    def __init__(self, height, width, y, x):
        CursesWindowWrapper.__init__(self, height, width, y, x)
        self.setTitle("Log")


class CursesInterface:
    """The class that asks input from the user."""

    # The screen
    __stdscr = None

    def __init__(self, burnerManager):
        """Constructor."""
        self.burnerManager = burnerManager
        self.__logs = accumulator.Accumulator()
        handler = logging.StreamHandler(self.__logs)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s - "
                                               "%(message)s", "%H:%M"))
        logging.getLogger().addHandler(handler)

    def live(self):
        """Ask user for commands. Return when user wants to quit."""
        curses.wrapper(self.__liveActually)
    
    def __updateLog(self):
        """Updates the log window with the latest log messages."""
        try:
            while True:
                self.__logWindow.addLine(self.__logs.pop())
        except IndexError:
            # All log messages read
            pass
        self.__logWindow.refresh()

    def __liveActually(self, stdscr):
        """live() calls this function inside a curses wrapper."""
        self.__stdscr = stdscr
        (screenH, screenW) = self.__stdscr.getmaxyx()
        self.__stdscr.addstr(0, 0, "Custom Burner " + common.version)
        self.__stdscr.addstr(screenH - 1, 0, "q: Quit")
        self.__stdscr.refresh()
        isoWindowHeight = ((screenH - 2) * 2)/ 3
        self.__isoWindow = IsoWindow(isoWindowHeight, screenW, 1, 0)
        self.__isoWindow.timeout(1000) # msec
        self.__logWindow = LogWindow(screenH - 2 - isoWindowHeight, screenW,
                                     isoWindowHeight + 1, 0)
        quitting = False
        while not quitting:
            c = self.__isoWindow.getch()
            self.__updateLog()
            if c == ord('q'):
                quitting = True
