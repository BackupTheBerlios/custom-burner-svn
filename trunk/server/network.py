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

import select
import SocketServer
import threading
import common
import socket
from burner_manager import *


def handshake(connection):
    """Handshake to a client.

    This function throws a BurnerException or socket.error in case of error"""
    connection.request.send(common.MSG_SERVER_GREETING + "\n")
    data = connection.readLine()
    if data != common.MSG_CLIENT_GREETING:
        raise common.BurnerException, "Strange data received: \"" + data + "\""
    connection.request.send(common.version + "\n")
    data = connection.readLine()
    if data != common.version:
        raise common.BurnerException, "Client version mismatch: " + data


class NetworkServerThread(threading.Thread):
    """Thread that waits continuously for new connections, until
    quitting becomes True."""

    def __init__(self, tcpServer, customBurnerServer):
        """Constructor."""
        threading.Thread.__init__(self)
        self.tcpServer = tcpServer
        self.customBurnerServer = customBurnerServer
    
    def run(self):
        """Main loop."""
        global quitting
        while not self.customBurnerServer.quitting:
            socks = (self.tcpServer.socket, )
            a = select.select(socks, (), socks, 1)
            if len(a[0]) > 0 or len(a[2]) > 0:
                self.tcpServer.handle_request()


class TCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """Multi-threaded TCP server.

    This class just inherits from the SocketServer module.
    """

    # We allow reusing an address
    allow_reuse_address = True


class RequestHandler(common.RequestHandler):
    """Handles network requests.

    The server side protocol is implemented here.
    """

    def greetPeer(self):
        """Receives self-introducing data from a burner and registers it."""
        peerName = self.readLine()
        peerPort = self.readLine()
        peerIP = self.request.getpeername()[0]
        self.logger.info("Registering burner %s, IP: %s, port: %s" %
                         (peerName, peerIP, peerPort))
        self.burnerManager.registerBurner(peerName, peerIP, peerPort)
        self.request.send(common.MSG_ACK + "\n")

    def handle(self):
        """Handle the connection: greet the peer."""
        self.burnerManager = BurnerManager.instance()
        try:
            handshake(self)
            data = self.readLine()
            if data == common.MSG_CLIENT_REGISTER:
                self.request.send(common.MSG_ACK + "\n")
                self.greetPeer()
            elif data == common.MSG_BURN_SUCCESS:
                burnerName = self.readLine()
                isoName = self.readLine()
                committer = self.readLine()
                self.request.send(common.MSG_ACK + "\n")
                self.logger.info("Peer %s report completion of job %s for %s" %
                                 (burnerName, isoName, committer))
                self.burnerManager.reportCompletion(burnerName, isoName)
            elif data == common.MSG_BURN_ERROR:
                burnerName = self.readLine()
                isoName = self.readLine()
                committer = self.readLine()
                self.request.send(common.MSG_ACK + "\n")
                self.logger.info(("Peer %s report error while burning %s " \
                                  "for %s") % (burnerName, isoName, committer))
                self.burnerManager.reportBurningError(burnerName, isoName)
            else:
                raise common.BurnerException, \
                      "Strange data received from client: \"%s\"" % data
        except common.BurnerException, e:
            self.logger.error(e)
        except socket.error, e:
            self.logger.error(e)

