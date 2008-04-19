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

import sys

class UserInterface:
    """The class that asks input from the user."""

    def __init__(self, isoDatabase, burnerManager):
        """Constructor.
        """
        self.isoDatabase = isoDatabase
        self.burnerManager = burnerManager

    def __isoMenu(self):
        """Shows a menu for burning an iso."""
        endMenu = False
        while not endMenu:
            print "Select an ISO from the list:"
            i = 0
            isoNum = len(self.isoDatabase.isos)
            for i in range(isoNum):
                print "%2d: %s" % (i + 1, self.isoDatabase.isos[i])
            print
            print "Your selection (0 exits):",
            try:
                temp = int(sys.stdin.readline())
                if temp == 0:
                    endMenu = True
                else:
                    iso = self.isoDatabase.isos[temp - 1]
                    print "For whom? ",
                    committer = sys.stdin.readline().strip()
                    print
                    print "Confirm burning %s for %s? (y/n):" % \
                          (iso, committer),
                    temp = sys.stdin.readline().strip()
                    if temp.lower() == "y":
                        self.burnerManager.queueIso(iso, committer)
                        endMenu = True
                    # Else just ask again
            except ValueError, e:
                pass # We just show the menu again

    def __listPendingIsos(self):
        """Lists the isos waiting to be burnt."""
        isos = self.burnerManager.getPendingIsos()
        print
        if len(isos) > 0:
            print "Pending isos:", len(isos)
            for iso in isos:
                print iso["date"], iso["iso"], iso["committer"]
        else:
            print "No isos pending."
        print

    def __listBurntIsos(self):
        """Lists the isos that have been burnt."""
        isos = self.burnerManager.getBurntIsos()
        print
        if len(isos) > 0:
            print "Burnt isos:", len(isos)
            for iso in isos:
                print iso["date"], iso["iso"], iso["committer"], iso["burner"]
        else:
            print "No isos burnt."
        print

    def __listWorkedIsos(self):
        """Lists the isos that are being burnt."""
        isos = self.burnerManager.getIsosBeingBurnt()
        print
        if len(isos) > 0:
            print "Isos currently being burnt:", len(isos)
            for iso in isos:
                print iso["date"], iso["iso"], iso["committer"], iso["burner"]
        else:
            print "No isos currently being burnt."
        print
    

    def live(self):
        """Ask user for commands. Return when user wants to quit."""
        quitting = False
        while not quitting:
            print "Enter a command from the list:"
            print
            print "a : add an iso to the queue"
            print "l : list queue of pending isos"
            print "w : list isos being burnt"
            print "d : list burnt isos"
            print "r : refresh queues, check for free burners and " \
                  "unassigned jobs."
            print "q : quit"
            print
            print "Your choice:",
            c = sys.stdin.readline().strip()
            if c == "a":
                self.__isoMenu()
            elif c == "l":
                self.__listPendingIsos()
            elif c == "w":
                self.__listWorkedIsos()                
            elif c == "d":
                self.__listBurntIsos()
            elif c == "r":
                self.burnerManager.refresh()
            elif c == "q":
                quitting = True


