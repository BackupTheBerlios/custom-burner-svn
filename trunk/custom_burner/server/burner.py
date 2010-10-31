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

import socket
import logging
from custom_burner import common
import network

class Burner:
    """Represents a burner.

    Instance variables:

    name: name, uniquely identifying this burner
    
    ip: IP address of this burner

    port: TCP port on which the burner is waiting for connections

    free: True if the burner is idle
    
    iso: name of the iso being burnt
    
    isos: list of the isos we can burn
    
    committer: the name of the committer for the ISO being burnt
    
    logger: logger object
    """

    def __init__(self, name, ip, port, isos):
        """Constructor.

        name: the name of the burner.
        ip: the IP address.
        port: the TCP port the burner will wait for connections on.
        isos: a list of the isos this burner can burn.
        """
        self.name = name
        self.ip = ip
        self.port = int(port)
        self.free = True
        self.isos = isos
        self.iso = ""
        self.committer = None
        self.logger = logging.getLogger("Burner(%s)" % self.name)

    def __getstate__(self):
        """Return the state of this object, for serialization."""
        odict = self.__dict__.copy()
        del odict["logger"]
        return odict

    def __setstate__(self, idict):
        self.__dict__.update(idict)
        self.logger = logging.getLogger("Burner(%s)" % self.name)

    def assignIso(self, date, iso, committer):
        """Tries to assign an iso to the burner.

        Returns true if the operation was succesful, that is: the burner is
        burning."""
        try:
            try:
                connection = common.RequestMaker(self.ip, self.port)
            except socket.error, e:
                raise common.BurnerException, "assignIso: Socket error: " + \
                      str(e)
            network.handshake(connection)
            connection.send("%s\n%s\n%s\n%s\n" %
                            (common.MSG_REQUEST_BURN, date, iso, committer))
            data = connection.readLine()
            if data == common.MSG_ACK:
                retval = True # Succesful!
                self.free = False
                self.iso = iso
                self.committer = committer
            elif data == common.MSG_NO_SUCH_ISO:
                self.logger.debug("No such ISO: %s" % iso)
                retval = False
            else:
                raise common.BurnerException, \
                      ("Strange data from burner: \"%s\"" % data)
        except common.BurnerException, e:
            self.logger.error("assignIso: " + str(e))
            retval = False
        except socket.error, e:
            self.logger.error("assignIso:" + str(e))
            retval = False
        return retval

    def close(self):
        """Closes the connection with the burner."""
        if not self.free:
            self.logger.error("close: Closing the connection but the burner " \
                              "is still working")
        try:
            connection = common.RequestMaker(self.ip, self.port)
            network.handshake(connection)
            connection.send(common.MSG_CLOSING + "\n")
            data = connection.readLine()
            if data != common.MSG_ACK:
                raise common.BurnerException, \
                      "close: Server doesn't want to tell us goodbye: " \
                      "\"%s\"" % data
            connection.close()
            self.logger.debug("Connection closed.")
        except common.BurnerException, e:
            self.logger.error("close: " + str(e))
        except socket.error, e:
            self.logger.error("close: " + str(e))

