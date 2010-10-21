# -*- coding: utf-8 -*-

"""Custom Burner client main module
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
import os
import os.path
import logging
import socket
import SocketServer
import optparse
import common

quitting = False

def handshake(connection):
    """Handshake to a server.
    
    This function throws a BurnerException or socket.error in case of error"""
    data = connection.readLine()
    if data != common.MSG_SERVER_GREETING:
        raise common.BurnerException, "Strange data received: \"%s\"" % data
    connection.request.send(common.MSG_CLIENT_GREETING + "\n")
    data = connection.readLine()
    if data != common.version:
        raise common.BurnerException, "Server version mismatch: \"%s\"" % data
    connection.request.send(common.version + "\n")

class CustomBurnerClient:
    """A burner."""
    # TCP port to listen on
    port = None

    # Server IP address
    serverIP = None

    # Server TCP port
    serverPort = None

    # Our TCP server object
    tcpServer = None

    # Our logger
    logger = None

    # Our name
    name = None

    # List of the isos we have
    isos = []

    # Directory containing our isos
    isoDirectory = None


    def registerToServer(self):
        """Register to a burner server.

        All the information about the server and this burner are taken from
        object attributes."""
        try:
            self.logger.info("Connecting to %s:%d" % \
                             (self.serverIP, self.serverPort))
            connection = common.RequestMaker(self.serverIP, self.serverPort)
            handshake(connection)
            connection.send(common.MSG_CLIENT_REGISTER + "\n")
            data = connection.readLine()
            if data != common.MSG_ACK:
                raise common.BurnerException, \
                      "Server doesn't want to register us: \"%s\"" % data
            connection.send(self.name + "\n")
            connection.send(str(self.port) + "\n")
            data = connection.readLine()
            if data != common.MSG_ACK:
                raise common.BurnerException, \
                      "Server doesn't want to accept our registration: \"%s\"" \
                      % data
            connection.send(common.MSG_CLIENT_HAS_ISOS + "\n")
            connection.send(str(len(self.isos)) + "\n")
            for iso in self.isos:
                connection.send(iso + "\n")
            data = connection.readLine()
            if data != common.MSG_ACK:
                raise common.BurnerException, \
                      "Server doesn't like our isos: \"%s\"" % data
            self.logger.info("Registered to server.")
            connection.close()
        except common.BurnerException, e:
            self.logger.error(e)
            sys.exit(1)
        except socket.error, e:
            self.logger.error(e)
            sys.exit(1)


    def hasIso(self, name):
        """Return True if this burner has a copy of an iso file."""
        if name in self.isos:
            return True
        else:
            self.logger.debug("Server asked for ISO %s, that I don't have." %
                              name)                              
            return False


    def queue(self, date, iso, committer):
        """Get ready to burn."""
        self.isoToBurn = iso
        self.isoDate = date
        self.isoCommitter = committer

    def live(self):
        """Waits for jobs and does them."""
        while not quitting:
            self.logger.info("Waiting for server request...")
            self.tcpServer.handle_request()
            if self.isoToBurn:
                # Burn!
                self.logger.info("Burning %s for %s. "
                                 "Please insert disc and press ENTER" % \
                                 (self.isoToBurn, self.isoCommitter))
                sys.stdin.readline()
                a = os.system(self.burnCmd % self.isoToBurn)
                try:
                    connection = common.RequestMaker(self.serverIP,
                                                     self.serverPort)
                    handshake(connection)
                    if a == 0:
                        # Report succesful job
                        self.logger.info("ISO %s for %s burnt successfully." %
                                         (self.isoToBurn, self.isoCommitter))
                        connection.send(common.MSG_BURN_SUCCESS + "\n")
                    else:
                        # Report error
                        self.logger.error("Error while burning %s for %s!" %
                                          (self.isoToBurn, self.isoCommitter))
                        connection.send(common.MSG_BURN_ERROR + "\n")
                    connection.send("%s\n%s\n%s\n" %
                                    (self.name, self.isoToBurn,
                                     self.isoCommitter))
                    data = connection.readLine()
                    if data != common.MSG_ACK:
                        raise BurnerException, \
                              "Strange data from server: \"%s\"" % data
                    connection.close()
                except common.BurnerException, e:
                    self.logger.error(e)
                except socket.error, e:
                    self.logger.error(e)
                self.isoToBurn = False

    def sayGoodbye(self):
        """Say good bye to server.

        You should call this if this client wants to quit before the
        server is closed."""
        try:
            self.logger.info("Saying goodbye to server.")
            connection = common.RequestMaker(self.serverIP,
                                             self.serverPort)
            handshake(connection)
            connection.send(common.MSG_CLOSING + "\n")
            connection.send(self.name + "\n")
            data = connection.readLine()
            if data != common.MSG_ACK:
                self.logger.warning("Server didn't answer Ok to our goodbye, "
                                    "but \"%s\" instead" % data)
            connection.close()
        except common.BurnerException, e:
            self.logger.error(e)
        except socket.error, e:
            self.logger.error(e)


    def __findImages(self):
        """Scans self.isodirectory for image files.

        The local variable isos is populated."""
        self.isos = os.listdir(os.path.expanduser(self.isoDirectory))
        self.logger.debug("I can burn the following isos:" + str(self.isos))
                

    def __init__(self, name, isoDirectory, burnCmd, port, serverIP,
                 serverPort=1234):
        """Initializes the client.

        isoDirectory: path to the directory containing the ISO images.

        burnCmd: the command to burn an iso named '%s' (could contain spaces)
        """
        self.name = name
        self.isoDirectory = os.path.expanduser(isoDirectory)
        self.port = port
        self.serverIP = serverIP
        self.serverPort = serverPort
        self.logger = logging.getLogger("CustomBurnerClient")
        self.logger.info("Starting")
        self.__findImages()
        self.registerToServer()
        self.logger.debug("Starting to listen on port %d" % self.port)
        self.tcpServer = TCPServer(("", self.port),
                                   RequestHandler)
        self.burnCmd = burnCmd
        self.isoToBurn = False
        

class TCPServer(SocketServer.TCPServer):
    """Our TCP server.

    This class just inherits from the SocketServer module.
    """

    # We allow reusing an address
    allow_reuse_address = True


class RequestHandler(common.RequestHandler):
    """Handles network requests from the server.

    Part of the client side protocol is implemented here.
    """

    def handle(self):
        """Handle the connection: receive a command from the server."""
        global quitting, burner
        try:
            handshake(self)
            data = self.readLine()
            if data == common.MSG_CLOSING:
                self.logger.info("Server is closing.")
                self.request.send(common.MSG_ACK + "\n")
                quitting = True
            elif data == common.MSG_REQUEST_BURN:
                date = self.readLine()
                iso = self.readLine()
                committer = self.readLine()
                if burner.hasIso(iso):
                    burner.queue(date, iso, committer)
                    self.request.send(common.MSG_ACK + "\n")
                else:
                    self.request.send(common.MSG_NO_SUCH_ISO + "\n")
            else:
                raise common.BurnerException, \
                      "Strange data from server: \"%s\"" % data
        except common.BurnerException, e:
            self.logger.error(e)
        except socket.error, e:
            self.logger.error(e)


############
def BurnerMain():
    """Main"""
    global burner
    # Cmd-line arguments
    parser = optparse.OptionParser()
    # Default values
    parser.set_defaults(name="Toaster",
                        command="wodim driveropts=burnfree -data %s",
                        server="127.0.0.1",
                        directory=".",
                        port=1235,
                        serverport=1234)
    parser.add_option("-n", "--name", dest="name", help="sets the burner name")
    parser.add_option("-d", "--dir", dest="directory",
                      help="specifies the directory containing the isos")
    parser.add_option("-c", "--cmd", dest="command",
                      help="specifies the command to burn an iso named %s")
    parser.add_option("-p", "--port", dest="port", type="int",
                      help="specifies the TCP port for listening")
    parser.add_option("-s", "--server", dest="server",
                      help="specifies the hostname or IP address of the server")
    parser.add_option("-t", "--serverport", dest="serverport", type="int",
                      help="specifies the server'sTCP port")
    parser.add_option("-v", "--verbose", dest="verbosity",
                      action="count", help="increase verbosity")
    (opts, args) = parser.parse_args()

    if len(args) > 0:
        # We don't want cmdline arguments
        parser.print_help()
        sys.exit(-1)

    # Setup logger
    if opts.verbosity == None or opts.verbosity == 0:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel,
                        format='%(asctime)s %(name)-18s %(levelname)-8s %(message)s',
                        datefmt='%d %b %Y %H:%M:%S')


    try:
        burner = CustomBurnerClient(opts.name, opts.directory, opts.command,
                                    opts.port, opts.server, opts.serverport)
    except socket.error, e:
        # This may occur during server start
        sys.stderr.write("Socket error: %s\n" % str(e))
        sys.exit(-1)

    try:
        burner.live()
    except KeyboardInterrupt:
        # User killed this application, but the server is still running.
        burner.sayGoodbye()
