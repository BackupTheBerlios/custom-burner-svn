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
import optparse
import common
from user_interface import *
from network import *
from burner import *
from burner_manager import *

class CustomBurnerServer:
    """A server."""
    # Maximum number of clients allowed to connect
    MAX_CLIENTS = 10

    # TCP port to listen on
    port = None

    # Our TCP server object
    tcpServer = None

    # Our logger
    logger = None

    # Are we going to exit? (the threads look at this variable)
    quitting = False
    
    def __init__(self, isoDirectory, port):
        """Initializes the server.

        isoDirectory: path to the directory containing the ISO images.
        """
        self.port = port
        self.logger = logging.getLogger("CustomBurnerServer")
        self.logger.info("Starting...")
        self.logger.info("Starting server on %s:%d" % \
                         ("localhost", self.port))
        self.tcpServer = TCPServer(("localhost", self.port),
                                   RequestHandler)
        self.ui = UserInterface(BurnerManager.instance())
        self.listener = NetworkServerThread(self.tcpServer, self)

    def live(self):
        """Accept network connections and user interaction."""
        self.listener.start()
        self.ui.live()
        self.quitting = True
        self.listener.join()
        BurnerManager.instance().close()



############
def ServerMain():
    """Main"""
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-18s %(levelname)-8s %(message)s',
                        datefmt='%d %b %Y %H:%M:%S')

    # Cmd-line arguments
    parser = optparse.OptionParser()
    # Default values
    parser.set_defaults(directory=".",
                        port=1234)
    parser.add_option("-d", "--dir", dest="directory",
                      help="specifies the directory containing the isos")
    parser.add_option("-p", "--port", dest="port", type="int",
                      help="specifies the TCP port for listening")
    (opts, args) = parser.parse_args()

    if len(args) > 0:
        # We don't want cmdline arguments
        parser.print_help()
        sys.exit(-1)

    try:
        srv = CustomBurnerServer(opts.directory, opts.port)
    except socket.error, e:
        # This may occur during server start
        sys.stderr.write("Socket error: %s\n" % str(e))
        sys.exit(-1)

    srv.live()
