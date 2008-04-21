#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Custom Burner client-server common file
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
import select
import logging
import SocketServer

version="0.5"

class BurnerException(Exception):
    pass

class NetworkCommunicator:
    """Contains utility methods for network communication.

    The implementing class must have a socket object named 'request'."""
    data = "" # Buffer for readline

    def readLine(self):
        """Read a single line from the socket."""
        chunkSize = 16
        socks = (self.request, )
        while "\n" not in self.data:
            select.select(socks, (), socks) # Avoid busy waiting
            self.data += self.request.recv(chunkSize)
        index = self.data.find("\n")
        retVal = self.data[:index]
        self.data = self.data[(index + 1):]
        return retVal


class RequestMaker(NetworkCommunicator):
    """Utility class to connect to a peer and talk to it."""
    request = None; # Our socket

    def __init__(self, peerIP, peerPort):
        """Open the connection.

        Throws BurnerException.
        """
        try:
            self.request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.request.connect((peerIP, peerPort))
        except socket.error, e:
            raise BurnerException, "Socket error: " + str(e)

    def send(self, data):
        """Sends data."""
        bytesSent = 0;
        bytesToSend = len(data)
        # We may not manage to send all data together. Python docs say that
        # we are responsible for checking that all data has been sent.
        while bytesSent < bytesToSend:
            b = self.request.send(data[bytesSent:])
            bytesSent += b

    def close(self):
        """Closes the connection.

        All communication-related functions will fail after you call
        this method."""        
        self.request.close()

    
class RequestHandler(NetworkCommunicator, SocketServer.BaseRequestHandler):
    """Handles network requests.

    The server protocol must be implemented by the handle() method.
    """
    def setup(self):
        self.logger = logging.getLogger("RequestHandler")
        self.peerAddress = self.request.getpeername() # (name, port)
        self.logger.debug("Connection received from %s:%d" % self.peerAddress)

    def finish(self):
        self.logger.debug("Closing connection with %s:%d." % self.peerAddress)


# Server greeting
MSG_SERVER_GREETING = "Custom Burner Server"
# Client greeting
MSG_CLIENT_GREETING = "Custom Burner Client"
# Client asks to be registered
MSG_CLIENT_REGISTER = "Please register me"
# Client is going to list its isos
MSG_CLIENT_HAS_ISOS = "My isos are:"
# Server asks the burner to burn something
MSG_REQUEST_BURN = "Please burn"
# The burner reports success
MSG_BURN_SUCCESS = "Burn successful"
# The burner reports an error
MSG_BURN_ERROR = "Burn unsuccessful"
# Burner doesn't have an ISO
MSG_NO_SUCH_ISO = "I don't have it"
# Client or server is closing
MSG_CLOSING = "Bye bye"
# Generic acknowledge message
MSG_ACK = "Ok"

# Program version
version = "0.5"
