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
import cPickle

from burner import *

singleton = None

class BurnerManager:
    """This class manages the burners and the burnings. It tracks the global
    state and talks to each burner. It knows all the isos the burners have.

    This class must also save and restore its internal state.

    The name is the primary key to access the database."""
    # The file we save the data into
    dbFileName = "custom_burner_server.db"
    burners = {} # Indexed by burner name
    burnersLock = None
    isos = set() # A set of all the isos our burners have
    pendingIsos = [] # A list of dicts {"date", "iso", "committer"}
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
        self.burnersLock = threading.Lock()
        self.isosLock = threading.Lock()
        self.logger = logging.getLogger("BurnerManager")
        # Read saved data
        try:
            self.logger.debug("Loading saved data...")
            f = file(self.dbFileName, "r+")
            unpickler = cPickle.Unpickler(f)
            self.burners = unpickler.load()
            self.pendingIsos = unpickler.load()
            self.isosBeingBurnt = unpickler.load()
            self.isosBurnt = unpickler.load()            
            f.close()
            self.__rebuildIsoList()
        except IOError, e:
            self.logger.warning("Unable to read saved data from file %s (%s). "
                                "Starting from scratch." % \
                                (self.dbFileName, str(e)))
        except EOFError, e:
            self.logger.error("Unable to read saved data from file %s "
                              "(EOFError). Starting from scratch." %
                              self.dbFileName)


    def __saveState(self):
        """Saves the current state to dbFileName."""
        self.isosLock.acquire()
        self.burnersLock.acquire()
        self.logger.debug("Saving current state...")
        try:
            try:
                dbFile = file(self.dbFileName, "w")
                pickler = cPickle.Pickler(dbFile)
                pickler.dump(self.burners)
                pickler.dump(self.pendingIsos)
                pickler.dump(self.isosBeingBurnt)
                pickler.dump(self.isosBurnt)
                pickler.clear_memo()
                dbFile.close()
            except IOError, e:
                self.logger.error("Error while saving state: " + str(e))
        finally:
            self.isosLock.release()
            self.burnersLock.release()

    def getIsos(self):
        """Returns a sorted list containing all the isos all the burners 
        have."""
        retval = []
        self.isosLock.acquire()
        try:
            retval = list(self.isos)
            retval.sort()
        finally:
            self.isosLock.release()
        return retval


    def getPendingIsos(self):
        """Returns a copy of the list of isos waiting to be burnt.

        The list is in the same form as the local attribute isos."""
        retval = []
        self.isosLock.acquire()
        try:
            for iso in self.pendingIsos:
                retval.append(dict(iso))
        finally:
            self.isosLock.release()
        return retval

    def getBurntIsos(self):
        """Returns a copy of the list of isos already burnt.

        The list is in the same form as the local attribute isosBurnt."""
        retval = []
        self.isosLock.acquire()
        try:
            for iso in self.isosBurnt:
                retval.append(dict(iso))
        finally:
            self.isosLock.release()
        return retval


    def getIsosBeingBurnt(self):
        """Returns a copy of the list of isos being burnt.

        The list is in the same form as the local attribute isosBeingBurnt."""
        retval = []
        self.isosLock.acquire()
        try:
            for iso in self.isosBeingBurnt:
                retval.append(dict(iso))
        finally:
            self.isosLock.release()
        return retval


    def getBurners(self):
        """Returns a list of the registered burners.

        The list contains dict's with the following fields:
        \"name\"      : name of the burner;
        \"ip\"        : IP address
        \"port\"      : TCP port
        \"iso\"       : iso the burner is currently burning (or None)
        \"committer\" : the committer of the iso (or None)"""
        retval = []
        self.burnersLock.acquire()
        try:
            for burner in self.burners.values():
                entry = {"name":burner.name, "ip":burner.ip, "port":burner.port}
                if burner.free:
                    entry["iso"] = entry["committer"] = None
                else:
                    entry["iso"] = burner.iso
                    entry["committer"] = burner.committer                    
                retval.append(entry)
        finally:
            self.burnersLock.release()
        return retval


    def registerBurner(self, burnerName, burnerIP, burnerPort, isos):
        """Register a burner and its isos."""
        self.burnersLock.acquire()
        try:
            # If another burner with the same name was registered, we
            # warn the user and overwrite it
            if self.burners.has_key(burnerName):
                self.logger.warning("Burner %s is already registered" %
                                    burnerName)
            self.burners[burnerName] = Burner(burnerName, burnerIP,
                                              burnerPort, isos)
        finally:
            self.burnersLock.release()
        self.__rebuildIsoList()        
        self.__saveState()


    def close(self):
        """Close the connection with all the burners.

        Informs the burners that the server is exiting."""
        self.burnersLock.acquire()
        try:
            try:
                while True:
                    (temp, burner) = self.burners.popitem()
                    burner.close()
            except KeyError:
                pass # We popped out all the burners
        finally:
            self.burnersLock.release()
        self.__saveState()


    def queueIso(self, iso, committer):
        """Adds an ISO to the queue.

        Please note that the iso must be a valid filename, otherwise it will
        remain in the queue forever, because all clients will reject it."""
        self.isosLock.acquire()
        try:
            self.logger.debug("Adding %s for %s to the queue." %
                              (iso, committer))
            self.pendingIsos.append({"date": time.asctime(), "iso": iso,
                              "committer": committer})
        finally:
            self.isosLock.release()
        self.__saveState()


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
                    break;
            if not burner.free: # Sanity check
                self.logger.error("Something VERY strange happened: "
                                  "the burner %s doesn't seem to "
                                  "have been working on %s!" %
                                  (burnerName, iso))
        finally:
            self.isosLock.release()
            self.burnersLock.release()
        self.__saveState()


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
                        self.pendingIsos.insert(0, self.isosBeingBurnt[i])
                        del(self.isosBeingBurnt[i])
                        burner.free = True
                        break;
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
        self.__saveState()

 
    def reportClosingBurner(self, burnerName):
        """Takes a burner out of the list, because it's closing itself."""
        self.burnersLock.acquire()
        try:
            self.logger.debug("Forgetting burner %s" % burnerName)
            try:
                del(self.burners[burnerName])
            except KeyError:
                # Weird, but may happen during debugging
                self.logger.error("Burner %s was not known!" % burnerName)
        finally:
            self.burnersLock.release()
        self.__rebuildIsoList()
        self.__saveState()


    def __rebuildIsoList(self):
        """Rebuilds isos merging all the isos that the burners have."""
        self.burnersLock.acquire()
        self.isosLock.acquire()
        try:
            self.isos = set()
            for burner in self.burners.values():
                self.isos.update(burner.isos)
                # for iso in burner.isos:
                #    self.isos.add(iso)
        finally:
            self.burnersLock.release()
            self.isosLock.release()
        

    def refresh(self):
        """Checks if new isos are waiting and tries to assign them to idle
        burners."""
        self.isosLock.acquire()
        self.burnersLock.acquire()
        try:
            if len(self.pendingIsos) > 0:
                # We have pending isos!
                for isoData in self.pendingIsos[:]:
                    isoAssigned = False
                    burnerIterator = self.burners.itervalues()
                    try:
                        while not isoAssigned:
                            burner = burnerIterator.next()
                            if burner.free:
                                if burner.assignIso(isoData["date"],
                                                    isoData["iso"],
                                                    isoData["committer"]):
                                    self.logger.info("ISO %s assigned to %s." %
                                                     (isoData["iso"],
                                                      burner.name))
                                    self.pendingIsos.remove(isoData)
                                    isoData["burner"] = burner.name
                                    self.isosBeingBurnt.append(isoData)
                                    isoAssigned = True
                    except StopIteration:
                        # We finished iterating over burners
                        self.logger.warning("Could not assign %s to anybody." %
                                            isoData["iso"])
        finally:
            self.burnersLock.release()
            self.isosLock.release()        
        self.__saveState()
