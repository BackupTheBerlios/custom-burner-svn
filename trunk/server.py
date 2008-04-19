#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Custom Burner server
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
import time
import os
import os.path
import logging
import threading
import socket
import common
from server.user_interface import *
from server.network import *
from server.burner import *
from server.burner_manager import *

class CustomBurnerServer:
    """A server."""
    # Maximum number of clients allowed to connect
    MAX_CLIENTS = 10

    # TCP port to listen on
    TCP_PORT = 1234

    # Our ISO database object
    isoDatabase = None

    # Our TCP server object
    tcpServer = None

    # Our logger
    logger = None

    # Are we going to exit? (the threads look at this variable)
    quitting = False
    
    def __init__(self, isoDirectory):
        """Initializes the server.

        isoDirectory: path to the directory containing the ISO images.
        """
        self.logger = logging.getLogger("CustomBurnerServer")
        self.logger.info("Starting...")
        self.isoDatabase = IsoDatabase(isoDirectory)
        self.isoDatabase.findImages()
        self.tcpServer = TCPServer(("localhost", self.TCP_PORT),
                                   RequestHandler)
        self.ui = UserInterface(self.isoDatabase, burnerManager)
        self.listener = NetworkServerThread(self.tcpServer, self)

    def live(self):
        """Accept network connections and user interaction."""
        self.listener.start()
        self.ui.live()
        self.quitting = True
        self.listener.join()
        burnerManager.close()


class IsoDatabase:
    """The repository of ISO images.

    This classes knows which files are available and keeps the queues.
    """

    isos = [] # List of the ISO images we can burn

    def findImages(self):
        """Scans ISO_DIR for image files.

        The local variable isos is populated."""
        self.isos = os.listdir(os.path.expanduser(self.ISO_DIR))

    def __init__(self, isoDirectory):
        """Constructor.

        isoDirectory: the directory that contains the ISO images we want
        to serve.
        """
        self.ISO_DIR = isoDirectory
        self.findImages()



############
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-18s %(levelname)-8s %(message)s',
                    datefmt='%d %b %Y %H:%M:%S')

burnerManager = BurnerManager()
srv = CustomBurnerServer("~/temp/burner/shared")
srv.live()
