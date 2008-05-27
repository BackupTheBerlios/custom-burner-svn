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
import curses.ascii
import curses.wrapper
from custom_burner import common
import accumulator
import burner_manager

class CursesTable:
    """This is a wrapper of the curses.Window class that makes it
    behave like a table.

    We need to make a proxy because it's not possible to have
    curses.newwin() generate an instance of this class."""

    def __init__(self, height, width, y, x, columns, autoScroll=True):
        """Constructor (same parameters as curses.newwin(), plus:

        columns: list of column names.
        autoScroll: true if you want the window to scroll when you add lines."""
        self.__window = curses.newwin(height, width, y, x)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.__window.refresh()
        self.__firstShownLine = 0;
        self.__title = ""
        self.__focused = False        
        self.__columns = columns[:]
        self.__widths = dict()
        for key in columns:
            self.__widths[key] = 0
        self.__data = []
        self.__selectedRow = -1
        self.__autoScroll = autoScroll

    def getch(self):
        """Proxy for curses.window.getch()"""
        return self.__window.getch()

    def timeout(self, data):
        """Proxy for curses.window.timeout()"""
        return self.__window.timeout(data)

    def __drawBorder(self):
        """Draws the border and the title."""
        if self.__focused:
            self.__window.attron(curses.A_BOLD)
        else:
            self.__window.attroff(curses.A_BOLD)
        self.__window.border()
        self.__window.addstr(0, 1, self.__title)
        self.__window.attroff(curses.A_BOLD)
        self.__window.addstr(self.height - 1, self.width - 8,
                             "%d/%d" % (self.__firstShownLine + 1,
                                          len(self.__data)))

    def __printRow(self, i):
        """Displays the i-th row, but only if it's inside the viewport."""
        if i < len(self.__data) and i >= self.__firstShownLine and \
               i < self.__firstShownLine + self.height - 2:
            formatString = ""
            for f in self.__columns:
                formatString += "%("+ f + ")-" + str(self.__widths[f]) + "s  "
                text = formatString % self.__data[i]
                self.__window.addnstr(i - self.__firstShownLine + 1, 1, text,
                                      self.width - 2)

    def __refreshContent(self):
        """Redraws the window from scratch."""
        self.__window.clear()
        self.__drawBorder()
        for i in range(self.__firstShownLine,
                       self.__firstShownLine + self.height - 2):
            if self.__focused and i == self.__selectedRow:
                self.__window.attron(curses.A_BOLD)
            self.__printRow(i)
            self.__window.attroff(curses.A_BOLD)

    def scrollDown(self):
        """Scrolls the window down one line"""
        if self.__firstShownLine < len(self.__data) - 1:
            self.__firstShownLine += 1
            self.__refreshContent()
            self.__printRow(self.__firstShownLine + self.height - 2)
        else:
            curses.beep()
            
    def scrollUp(self):
        """Scrolls the window up one line"""
        if self.__firstShownLine > 0:
            self.__firstShownLine -= 1
            self.__refreshContent()
        else:
            curses.beep()

    def addRow(self, row):
        """Adds a row to the end of the table.

        Scrolls if this table is auto-scrolling.

        line: a dict with column names as keys."""
        self.__data.append(row.copy())
        # We may need to resize the table, to fit the new data
        for key in row.keys():
            if len(row[key]) > self.__widths[key]:
                self.__widths[key] = len(row[key])
        if self.__selectedRow == -1:
            self.__selectedRow = 0
        lines = len(self.__data)
        if self.__firstShownLine <= lines - self.height + 2 and \
               self.__autoScroll:
            # We need to scroll everything upwards
            self.scrollDown()
            if self.__selectedRow < self.__firstShownLine:
                self.__selectedRow = self.__firstShownLine
                if self.__focused:
                    self.__window.attron(curses.A_BOLD)
                    self.__printRow(self.__firstShownLine)
                    self.__window.attroff(curses.A_BOLD)
        else:
            if self.__focused and self.__selectedRow == lines - 1:
                self.__window.attron(curses.A_BOLD)
            self.__printRow(lines - 1)
            self.__window.attroff(curses.A_BOLD)
        self.__drawBorder()

    def setTitle(self, title):
        """Sets the window title"""
        self.__title = title
        self.__drawBorder()

    def refresh(self):
        return self.__window.refresh()

    def noutrefresh(self):
        return self.__window.noutrefresh()

    def focus(self):
        self.__focused = True
        self.__drawBorder()
        if self.__selectedRow > -1:
            self.__window.attron(curses.A_BOLD)
            self.__printRow(self.__selectedRow)
            self.__window.attroff(curses.A_BOLD)
        self.refresh()


    def unfocus(self):
        self.__focused = False
        self.__drawBorder()
        if self.__selectedRow > -1:
            self.__printRow(self.__selectedRow) # without bold face
        self.refresh()


    def receiveKey(self, key):
        """Reacts to a key pressed."""
        if key == curses.KEY_UP:
            if self.__selectedRow > 0:
                self.__printRow(self.__selectedRow)
                self.__selectedRow -= 1
                if self.__selectedRow < self.__firstShownLine:
                    self.scrollUp()
                else:
                    self.__window.attron(curses.A_BOLD)
                    self.__printRow(self.__selectedRow)
                    self.__window.attroff(curses.A_BOLD)
                self.refresh()
            else:
                curses.beep()                
        elif key == curses.KEY_DOWN:
            if self.__selectedRow < len(self.__data) - 1:
                self.__printRow(self.__selectedRow)
                self.__selectedRow += 1
                if self.__selectedRow == \
                       self.__firstShownLine + self.height - 2:
                    self.scrollDown()
                else:
                    self.__window.attron(curses.A_BOLD)
                    self.__printRow(self.__selectedRow)
                    self.__window.attroff(curses.A_BOLD)
                self.refresh()
            else:
                curses.beep()
        else:
            curses.beep()


class IsoWindow(CursesTable):
    """A window that displays the list of ISOs."""

    def __init__(self, height, width, y, x):
        CursesTable.__init__(self, height, width, y, x,
                             ("date", "iso", "committer"))
        self.setTitle("ISO queue")
        self.burnerManager = burner_manager.BurnerManager.instance()
        self.redisplay()

    def redisplay(self):
        """Redisplays the window content."""
        for iso in self.burnerManager.pendingIsos:
            self.addRow(iso)
        self.refresh()


class LogWindow(CursesTable):
    """A window that displays log messages."""

    def __init__(self, height, width, y, x):
        CursesTable.__init__(self, height, width, y, x, ("log", ))
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
                self.__logWindow.addRow({"log": self.__logs.pop()})
        except IndexError:
            # All log messages read
            pass
        self.__logWindow.refresh()


    def __switchFocus(self):
        """Moves the focus to another window."""
        if self.__focus == 0:
            self.__isoWindow.unfocus()
            self.__logWindow.focus()
            self.__focus = 1
            self.__focusedWindow = self.__logWindow
        else:
            self.__isoWindow.focus()
            self.__logWindow.unfocus()
            self.__focus = 0
            self.__focusedWindow = self.__isoWindow

    def __liveActually(self, stdscr):
        """live() calls this function inside a curses wrapper."""
        self.__stdscr = stdscr
        (screenH, screenW) = self.__stdscr.getmaxyx()
        self.__stdscr.addstr(0, 0, "Custom Burner " + common.version)
        self.__stdscr.addstr(screenH - 1, 0, "q: Quit")
        self.__stdscr.noutrefresh()
        isoWindowHeight = ((screenH - 2) * 2)/ 3
        self.__isoWindow = IsoWindow(isoWindowHeight, screenW, 1, 0)
        self.__isoWindow.timeout(1000) # msec
        self.__logWindow = LogWindow(screenH - 2 - isoWindowHeight, screenW,
                                     isoWindowHeight + 1, 0)
        self.__logWindow.noutrefresh()
        self.__focus = 0
        self.__focusedWindow = self.__isoWindow
        self.__isoWindow.focus()
        quitting = False
        while not quitting:
            self.__updateLog()
            c = self.__stdscr.getch()
            self.__stdscr.addstr(screenH - 1, 0, "q: Quit" + curses.unctrl(c))
            self.__stdscr.refresh()
            if c == curses.ascii.TAB:
                self.__switchFocus()
            elif c == ord('q'):
                quitting = True
            elif c != curses.ERR:
                self.__focusedWindow.receiveKey(c)
