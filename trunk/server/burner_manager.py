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

import threading
import logging
import time
import socket
from burner import *

singleton = None

class BurnerManager:
    """This class manages the burners and the burnings. It tracks the
    global state and talks to each burner.

    The name is the primary key to access the database."""
    burners = {} # Indexed by burner name
    burnersLock = None
    isos = [] # A list of dicts {"date", "iso", "committer"}
    # A list of dicts {"date", "iso", "committer", "burner"}
    isosBeingBurnt = []
    isosBurnt = [] # See isosBeingBurnt
    isosLock = None

    logger = None

    def instance():
        """This method creates the instance of the manager and returns it.

        This is not an actual singleton: it's just a way to ensure
        that everyone is using the same object."""
        global singleton
        if singleton == None:
            singleton = BurnerManager()
        return singleton

    instance = staticmethod(instance)

    def __init__(self):
        self.burnersLock = threading.RLock()
        self.isosLock = threading.RLock()
        self.logger = logging.getLogger("BurnerManager")


    def getPendingIsos(self):
        """Returns a copy of the list of isos waiting to be burnt.

        The list is in the same form as the local attribute isos."""
        retval = []
        for iso in self.isos:
            retval.append(dict(iso))
        return retval

    def getBurntIsos(self):
        """Returns a copy of the list of isos already burnt.

        The list is in the same form as the local attribute isosBurnt."""
        retval = []
        for iso in self.isosBurnt:
            retval.append(dict(iso))
        return retval

    def getIsosBeingBurnt(self):
        """Returns a copy of the list of isos being burnt.

        The list is in the same form as the local attribute isosBeingBurnt."""
        retval = []
        for iso in self.isosBeingBurnt:
            retval.append(dict(iso))
        return retval

    def registerBurner(self, burnerName, burnerIP, burnerPort):
        """Register a burner."""
        self.burnersLock.acquire()
        try:
            # We add the burner to the list only if it's not in there yet
            if not self.burners.has_key(burnerName):
                self.burners[burnerName] = Burner(burnerName, burnerIP,
                                                  burnerPort)
            else:
                self.logger.warning("Burner %s is already registered" %
                                    burnerName)
        finally:
            self.burnersLock.release()

    def close(self):
        """Close the connection with all the burners.

        Informs the burners that the server is exiting."""
        self.burnersLock.acquire()
        try:
            try:
                (temp, burner) = self.burners.popitem()
                burner.close()
            except KeyError:
                pass # We popped out all the burners
        finally:
            self.burnersLock.release()

    def queueIso(self, iso, committer):
        """Adds an ISO to the queue.

        Please note that the iso must be a valid filename, otherwise it will
        remain in the queue forever, because all clients will reject it."""
        self.isosLock.acquire()
        try:
            self.logger.debug("Adding %s for %s to the queue." %
                              (iso, committer))
            self.isos.append({"date": time.asctime(), "iso": iso,
                              "committer": committer})
        finally:
            self.isosLock.release()

    def reportCompletion(self, burnerName, iso):
        """Reports a successful burn."""
        self.isosLock.acquire()
        self.burnersLock.acquire()
        try:
            burner = self.burners[burnerName]
            for i in range(len(self.isosBeingBurnt)):
                if self.isosBeingBurnt[i]["burner"] == burnerName:
                    # Found
                    self.isosBurnt.append(self.isosBeingBurnt[i])
                    del(self.isosBeingBurnt[i])
                    burner.free = True
            if not burner.free: # Sanity check
                logger.error("Something VERY strange happened: " \
                             "the burner " + burnerName + " doesn't seem to " \
                             "have been working on " + iso + "!")
        finally:
            self.isosLock.release()
            self.burnersLock.release()

    def reportBurningError(self, burnerName, iso):
        """Reports an unsuccessful burn."""
        self.isosLock.acquire()
        self.burnersLock.acquire()
        try:
            # It might happen that the burner is not in the queue any
            # more, because we have just sent it a goodbye message
            # from another thread. This shouldn't happen, but may
            # happen. So it must be handled.
            try:
                burner = self.burners[burnerName]
                for i in range(len(self.isosBeingBurnt)):
                    if self.isosBeingBurnt[i]["burner"] == burnerName:
                        # Found: we put it into the head of the waiting queue.
                        # This will have the additional "burner" field, that
                        # we will easily ignore.
                        self.isos.insert(0, self.isosBeingBurnt[i])
                        del(self.isosBeingBurnt[i])
                        burner.free = True
                if not burner.free: # Sanity check
                    self.logger.error("Something VERY strange happened: "
                                      "the burner %s doesn't seem to have "
                                      "been working on %s!" %
                                      (burnerName, iso) )
            except KeyError:
                self.logger.error("Burner named %s is not in the database." %
                                  burnerName)
        finally:
            self.isosLock.release()
            self.burnersLock.release()

    def refresh(self):
        """Checks if new isos are waiting and tries to assign them to idle
        burners."""
        self.isosLock.acquire()
        self.burnersLock.acquire()
        try:
            if len(self.isos) > 0:
                # We have pending isos!
                done = False
                for i in range(len(self.isos)):
                    isoData = self.isos[i]
                    burnerIterator = self.burners.itervalues()
                    try:
                        while not done:
                            burner = burnerIterator.next()
                            if burner.free:
                                if burner.assignIso(isoData["date"],
                                                    isoData["iso"],
                                                    isoData["committer"]):
                                    self.logger.info("ISO %s assigned to %s." %
                                                     (isoData["iso"],
                                                      burner.name))
                                    isoData["burner"] = burner.name
                                    self.isosBeingBurnt.append(isoData)
                                    del(self.isos[i])
                                    done = True
                    except StopIteration:
                        pass # We finished iterating over burners
                    if done:
                        break
        finally:
            self.burnersLock.release()
            self.isosLock.release()        
