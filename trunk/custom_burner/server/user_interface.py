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
import csv

class UserInterface:
    """The class that asks input from the user."""

    def __init__(self, burnerManager):
        """Constructor.
        """
        self.burnerManager = burnerManager

    def __isoMenu(self):
        """Shows a menu for burning an iso."""
        endMenu = False
        while not endMenu:
            print "Select an ISO from the list:"
            i = 0
            isos = self.burnerManager.getIsos()
            isoNum = len(isos)
            if isoNum == 0:
                print "No isos available! You need to connect a burner!"
                return
            for i in range(isoNum):
                print "%2d: %s" % (i + 1, isos[i])
            print
            print "Your selection (0 exits):",
            try:
                temp = int(sys.stdin.readline())
                if temp == 0:
                    endMenu = True
                else:
                    iso = isos[temp - 1]
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

    def __deletePendingIso(self):
        """Lists the isos waiting to be burnt."""
        isos = self.burnerManager.getPendingIsos()
        print
        if len(isos) > 0:
            print "Pending isos:", len(isos)
            for i in range(len(isos)):
                iso = isos[i]
                print i + 1, ":", iso["date"], iso["iso"], iso["committer"]
            try:
                choice = int(raw_input("ISO to delete: ")) - 1
                confirmation = raw_input("Confim deleting iso %s for %s "
                                         "(y/n): " % 
                                         (isos[choice]["iso"],
                                          isos[choice]["committer"]))
                if confirmation.lower() == "y":
                    self.burnerManager.removeIso(isos[choice])
            except ValueError:
                pass # Annulliamo
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


    def __outputCSV(self):
        """Outputs a list of the isos that have been burnt in CSV format,
        together with some statistics."""
        fileName = "burntIsos.csv"
        isos = self.burnerManager.getBurntIsos()
        if len(isos) > 0:
            print "Filename [%s]: " % (fileName),
            c = sys.stdin.readline().strip()
            if c:
                fileName = c
            try:
                outFile = csv.writer(open(fileName, "w"))
                outFile.writerow(["No.", "Req. date", "ISO", "Committer",
                                  "Burner"])
                isosCounters = dict()
                burnersCounters = dict()
                i = 1
                for iso in isos:
                    outFile.writerow([i, iso["date"], iso["iso"],
                                      iso["committer"], iso["burner"]])
                    if iso["iso"] in isosCounters:
                        isosCounters[iso["iso"]] += 1
                    else:
                        isosCounters[iso["iso"]] = 1
                    if iso["burner"] in burnersCounters:
                        burnersCounters[iso["burner"]] += 1
                    else:
                        burnersCounters[iso["burner"]] = 1
                    i += 1
                # Statistics
                secondMember = lambda x:x[1] # Needed for sort() below
                outFile.writerow([])
                outFile.writerow(["ISO Statistics"])
                outFile.writerow(["ISO", "Requests"])
                items = isosCounters.items()
                items.sort(key=secondMember, reverse=True)
                for item in items:
                    outFile.writerow(list(item))
                outFile.writerow([])
                outFile.writerow(["Burners Statistics"])
                outFile.writerow(["Burner", "ISOs burnt"])
                items = burnersCounters.items()
                items.sort(key=secondMember, reverse=True)
                for item in items:
                    outFile.writerow(list(item))
            except IOError, e:
                sys.stderr.write(str(e) + "\n")
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
    

    def __listBurners(self):
        """Lists the burners registered to this server."""
        burners = self.burnerManager.getBurners()
        print
        if len(burners) > 0:
            print "Burners:", len(burners)
            for burner in burners:
                print burner["name"], burner["ip"] + ":" + str(burner["port"]),
                if burner["iso"] != None:
                    print "burning", burner["iso"], "for", burner["committer"]
                else:
                    print "idle"
        else:
            print "No burners registered."
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
            print "c : output burnt isos in CSV format"
            print "b : list burners"
            print "r : refresh queues, check for free burners and " \
                  "unassigned jobs."
            print "D : delete pending iso"
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
            elif c == "c":
                self.__outputCSV()
            elif c == "d":
                self.__listBurntIsos()
            elif c == "D":
                self.__deletePendingIso()
            elif c == "b":
                self.__listBurners()
            elif c == "r":
                self.burnerManager.refresh()
            elif c == "q":
                quitting = True


