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
import curses.panel
import curses.textpad
from custom_burner import common
import accumulator
import burner_manager

def errorMessage(message):
    """Displays an error message."""
    winY = screenH / 2 - 2 
    winX = (screenW - len(message)) / 2 + 2
    winWidth = len(message) + 4
    if len(message) < 5:
        winWidth = 9
    panel = CursesPanel(5, winWidth, winY, winX, "Error")
    panel.focus()
    panel._window.addstr(2, 2, message)
    panel.getch()
    del panel


def askString(message, length=40):
    """Asks the user to enter a string.

    message: the window title.
    length: expected maximum length for the string.

    Returns the inserted string or None if the user canceled the input."""
    retval = None
    winY = screenH / 2 - 2
    winWidth = max(len(message), length) + 4
    winX = (screenW - winWidth) / 2
    panel = CursesPanel(3, winWidth, winY, winX, title=message)
    panel.focus()
    window = panel._window
    subWin = window.derwin(1, length, 1, 1)
    subWin.keypad(1)
    textBox = curses.textpad.Textbox(subWin)
    textBox.stripspaces = True
    curses.panel.update_panels()
    curses.doupdate()
    done = False
    while not done:
        c = subWin.getch()
        if c == curses.ascii.NL:
            retval = textBox.gather()
            done = True
        elif c == curses.ascii.ESC:
            done = True # so that we return None
        else:
            textBox.do_command(c)
    del textBox
    del subWin
    del window
    return retval


class CursesPanel:
    """This is a wrapper of the curses.Window class that makes use of
    the curses.panel module.

    The window support focusing: it changes its appearance.

    We need to make a wrapper because it's not possible to have
    curses.newwin() generate an instance of this class."""

    # Our panel object
    __panel = None

    # Our title
    __title = None

    # Our window object
    _window = None

    # True if we have focus
    _focused = False

    # Coordinates
    x = 0
    y = 0

    # Dimensions
    width = 0
    height = 0
    
    def __init__(self, height, width, y, x, title=""):
        """Constructor (same parameters as curses.newwin(), plus:

        title: the window title."""
        self._window = curses.newwin(height, width, y, x)
        self._window.keypad(1)
        self.__panel = curses.panel.new_panel(self._window)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.__title = title
        self.drawBorder()

    def __del__(self):
        """Destructor: we explicitly destroy the curses window object."""
        del self.__panel
        del self._window

    def setTitle(self, title):
        """Sets the window title"""
        self.__title = title
        self.drawBorder()

    def timeout(self, data):
        """Proxy for curses.window.timeout()"""
        return self._window.timeout(data)

    def drawBorder(self):
        """Draws the border and the title."""
        if self._focused:
            self._window.attron(curses.A_BOLD)
        else:
            self._window.attroff(curses.A_BOLD)
        self._window.border()
        self._window.addstr(0, 1, self.__title)
        self._window.attroff(curses.A_BOLD)

    def getch(self):
        """Proxy for curses.window.getch()."""
        return self._window.getch()

    def focus(self):
        """Reives focus."""
        self._focused = True
        self.drawBorder()

    def unfocus(self):
        """Loses focus."""
        self._focused = False
        self.drawBorder()


class CursesTable(CursesPanel):
    """A CursesPanel that displays tabular data."""

    def __init__(self, height, width, y, x, columns, title="", autoScroll=True):
        """Constructor (same parameters as curses.newwin(), plus:

        columns: list of column names.
        autoScroll: true if you want the window to scroll when you add lines."""
        CursesPanel.__init__(self, height, width, y, x, title)
        self.__firstShownLine = 0;
        self._focused = False        
        self.__columns = columns[:]
        self.__widths = dict()
        self.__autoScroll = autoScroll
        self.clear()

    def getch(self):
        """Waits for a keypress and interprets it."""
        c = CursesPanel.getch(self)
        if c != curses.ERR:
            self.receiveKey(c)
        return c

    def focus(self):
        """Reives focus."""
        CursesPanel.focus(self)
        if self.__selectedRow > -1:
            self._window.attron(curses.A_BOLD)
            self.__printRow(self.__selectedRow)
            self._window.attroff(curses.A_BOLD)

    def unfocus(self):
        """Loses focus."""
        CursesPanel.unfocus(self)
        if self.__selectedRow > -1:
            self.__printRow(self.__selectedRow) # without bold face

    def __makeFormatString(self):
        """Prepares the content of the variable __formatString."""
        self.__formatString = ""
        for f in self.__columns:
            self.__formatString += "%("+ f + ")-" + str(self.__widths[f]) + \
                                   "s  "

    def __printRow(self, i):
        """Displays the i-th row, but only if it's inside the viewport."""
        if i < len(self.__data) and i >= self.__firstShownLine and \
               i < self.__firstShownLine + self.height - 2:
            text = self.__formatString % self.__data[i]
            self._window.addnstr(i - self.__firstShownLine + 1, 1, text,
                                      self.width - 2)

    def clear(self):
        """Clears the internal table data and the window content."""
        for key in self.__columns:
            self.__widths[key] = 0
        self.__data = []
        self.__selectedRow = -1
        self.__formatString = ""
        self._window.clear()
        self.drawBorder()        

    def __refreshContent(self):
        """Redraws the window from scratch.

        This is useful, for instance, when the fields' sizes have changed, and
        all the rows must be redisplayed."""
        self._window.clear()
        self.drawBorder()
        for i in range(self.__firstShownLine,
                       self.__firstShownLine + self.height - 2):
            if self._focused and i == self.__selectedRow:
                self._window.attron(curses.A_BOLD)
            self.__printRow(i)
            self._window.attroff(curses.A_BOLD)

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
                self.__makeFormatString()
                self.__refreshContent()
        if self.__selectedRow == -1:
            self.__selectedRow = 0
        lines = len(self.__data)
        if self.__firstShownLine <= lines - self.height + 2 and \
               self.__autoScroll:
            # We need to scroll everything upwards
            self.scrollDown()
            if self.__selectedRow < self.__firstShownLine:
                self.__selectedRow = self.__firstShownLine
                if self._focused:
                    self._window.attron(curses.A_BOLD)
                    self.__printRow(self.__firstShownLine)
                    self._window.attroff(curses.A_BOLD)
        else:
            if self._focused and self.__selectedRow == lines - 1:
                self._window.attron(curses.A_BOLD)
            self.__printRow(lines - 1)
            self._window.attroff(curses.A_BOLD)


    def receiveKey(self, key):
        """Reacts to a key pressed.

        You should explicitly call this method only if you didn't call
        the object's getch()."""
        if key == curses.KEY_UP:
            if self.__selectedRow > 0:
                self.__printRow(self.__selectedRow)
                self.__selectedRow -= 1
                if self.__selectedRow < self.__firstShownLine:
                    self.scrollUp()
                else:
                    self._window.attron(curses.A_BOLD)
                    self.__printRow(self.__selectedRow)
                    self._window.attroff(curses.A_BOLD)
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
                    self._window.attron(curses.A_BOLD)
                    self.__printRow(self.__selectedRow)
                    self._window.attroff(curses.A_BOLD)
            else:
                curses.beep()

    def getSelectedRow(self):
        """Returns the number of the currently selected row.

        -1 means no row is selected."""
        return self.__selectedRow


class IsoWindow(CursesTable):
    """A window that displays the list of ISOs."""

    def __init__(self, height, width, y, x):
        CursesTable.__init__(self, height, width, y, x,
                             ("date", "iso", "committer"), title="ISO Queue",
                             autoScroll=False)
        self.burnerManager = burner_manager.BurnerManager.instance()
        self.reloadData()

    def reloadData(self):
        """Refresh the iso list and redisplays it."""
        self.clear()
        for iso in self.burnerManager.getPendingIsos():
            self.addRow(iso)


class IsoSelectorWindow(CursesTable):
    """A window that displays the list of available ISOs and allows
    the user to choose one."""

    def __init__(self, height, width, y, x):
        CursesTable.__init__(self, height, width, y, x, ("iso",),
                             title="Available ISOs", autoScroll=False)
        self.burnerManager = burner_manager.BurnerManager.instance()
        self.__isos = []
        for i in self.burnerManager.getIsos():
            entry = {"iso": i}
            self.__isos.append(entry)
            self.addRow(entry)

    def live(self):
        """Requests user input.

        Returns the ISO name or None if the user canceled the selection."""
        retval = None
        done = False
        self.focus()
        if len(self.__isos) == 0:
            self.unfocus()
            errorMessage("No isos available!")
            return None
        while not done:
            c = self.getch()
            if c == curses.ascii.NL:
                retval = self.__isos[self.getSelectedRow()]["iso"]
                done = True
            if c == curses.ascii.ESC or c == ord('q'):
                done = True
        return retval
        

class LogWindow(CursesTable):
    """A window that displays log messages."""

    def __init__(self, height, width, y, x):
        CursesTable.__init__(self, height, width, y, x, ("log", ), title="Log",
                             autoScroll = True)


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

    def __askForIso(self):
        """Asks the user for an iso to queue: which iso, for whom."""
        self.__focusedWindow.unfocus()
        questionWindow = IsoSelectorWindow(screenH / 2,
                                           screenW / 2, screenH / 4,
                                           screenW / 4)
        chosenIso = questionWindow.live()
        self.__focusedWindow.focus()
        del questionWindow
        curses.panel.update_panels()
        curses.doupdate()
        if chosenIso != None:
            committer = askString("For whom is this ISO?")
            curses.panel.update_panels()
            curses.doupdate()
            if committer != None:
                self.burnerManager.queueIso(chosenIso, committer)
                self.__isoWindow.reloadData()
                curses.panel.update_panels()
                curses.doupdate()
        

    def __liveActually(self, stdscr):
        """live() calls this function inside a curses wrapper."""
        global screenH, screenW
        self.__stdscr = stdscr
        (screenH, screenW) = self.__stdscr.getmaxyx()
        self.__stdscr.addstr(0, 0, "Custom Burner " + common.version)
        self.__stdscr.addstr(screenH - 1, 0, "a: add ISO  q: Quit")
        self.__stdscr.noutrefresh()
        isoWindowHeight = ((screenH - 2) * 2)/ 3
        self.__isoWindow = IsoWindow(isoWindowHeight, screenW, 1, 0)
        self.__isoWindow.timeout(1000) # msec
        self.__logWindow = LogWindow(screenH - 2 - isoWindowHeight, screenW,
                                     isoWindowHeight + 1, 0)
        self.__focus = 0
        self.__focusedWindow = self.__isoWindow
        self.__isoWindow.focus()
        quitting = False
        while not quitting:
            self.__updateLog()
            curses.panel.update_panels()
            curses.doupdate()
            c = self.__focusedWindow.getch()
            if c == curses.ascii.TAB:
                self.__switchFocus()
            elif c == ord('a'):
                self.__askForIso()
            elif c == ord('q'):
                quitting = True
