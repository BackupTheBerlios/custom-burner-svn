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
import time
import socket
import SocketServer
import optparse
import dbus

import common


def handshake(connection):
    """Handshake to a server.

    connection: a socket object connected to the server.
    
    Throws a BurnerException or socket.error in case of error"""
    data = connection.readLine()
    if data != common.MSG_SERVER_GREETING:
        raise common.BurnerException, "Strange data received: \"%s\"" % data
    connection.request.send(common.MSG_CLIENT_GREETING + "\n")
    data = connection.readLine()
    if data != common.version:
        raise common.BurnerException, "Server version mismatch: \"%s\"" % data
    connection.request.send(common.version + "\n")


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
        global burner
        try:
            handshake(self)
            data = self.readLine()
            if data == common.MSG_CLOSING:
                self.logger.info("Server is closing.")
                self.request.send(common.MSG_ACK + "\n")
                burner.quitting = True
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


class CustomBurnerClient:
    """A burner.

    Instance variables.

    name: the name of the burner (from the cmd line)
    
    port: the TCP port to listen on
    
    serverIP: the IP address of the server
    
    serverPort: the TCP port of the server to connect to
    
    tcpServer: a TCPServer object that is used to listen for messages
    coming from the server.

    logger: logger object

    isoDirectory: path to the directory containing the ISOs

    isos: a list of all the ISOs inside isoDirectory

    quitting: if set to True, the live() method ends

    burnCmd: the command for burning an ISO named %s

    burnCmdForced: if True, the value of burnCmd must not be rewritten
    by setBurnParameters().

    You shold immediately call forceBurnCommand() and/or
    setBurnParameters().
    """

    def __init__(self, name, isoDirectory, port, serverIP,
                 serverPort=1234):
        """Initializes the client.

        isoDirectory: path to the directory containing the ISO images.

        """
        self.name = name
        self.isoDirectory = os.path.expanduser(isoDirectory)
        self.port = port
        self.serverIP = serverIP
        self.serverPort = serverPort
        self.burnCmd = None
        self.device = None
        self.speed = None
        self.isoToBurn = False
        self.quitting = False
        # Initialize logging
        self.logger = logging.getLogger("CustomBurnerClient")
        self.logger.info("Starting")
        # Scan self.isodirectory for image files.
        self.isos = os.listdir(os.path.expanduser(self.isoDirectory))
        self.logger.debug("I can burn the following isos:" + str(self.isos))
        # Register to server and start listening
        self.__registerToServer()
        self.logger.debug("Starting to listen on port %d" % self.port)
        self.tcpServer = TCPServer(("", self.port), RequestHandler)
        self.burnCmdForced = False

    def forceBurnCommand(self, cmd):
        """Sets a custom command for burning CD's
        
        cmd: the command to burn an iso named '%s' (could contain spaces)
        """
        self.burnCmd = cmd
        self.burnCmdForced = True

    def setBurnParameters(self, device, speed):
        """Sets the command for burning CD's
        
        device: the burner device file.

        speed: the burning speed.

        Constructs self.burnCmd as an invocation of cdrecord with the
        specified parameters.
        """
        self.device = device
        self.speed = speed
        if not self.burnCmdForced:
            self.burnCmd = ("cdrecord dev=%s speed=%d driveropts=burnfree -v "
                            "-eject -data %%s" % (device, speed))

    def __connectToServer(self):
        """Connects to the server and goes through the handshake procedure.

        Returns a common.RequestMaker object.

        Raises BurnerException or socket.error in case of error.
        """
        retval = common.RequestMaker(self.serverIP, self.serverPort)
        try:
            handshake(retval)
            return retval
        except:
            retval.close()
            raise

    def __registerToServer(self):
        """Register to a burner server.

        All the information about the server and this burner are taken from
        object attributes."""
        try:
            self.logger.info("Connecting to %s:%d" % \
                             (self.serverIP, self.serverPort))
            connection = self.__connectToServer()
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

    def __waitForDiscUDisks(self, systemBus):
        """Waits for the disc to be inserted using UDisks.
        
        Raises dbus.exceptions.DBusException or common.BurnerException
        in case of error.
        """
        proxy = systemBus.get_object("org.freedesktop.UDisks", 
                                     "/org/freedesktop/UDisks")
        interface = dbus.Interface(proxy, "org.freedesktop.UDisks")
        objectPath = interface.FindDeviceByDeviceFile(self.device)
        device = systemBus.get_object("org.freedesktop.UDisks", 
                                      objectPath)
        mediaCompatibility = device.Get("", "DriveMediaCompatibility")
        if ((not "optical_cd_r" in mediaCompatibility) or 
            (not "optical_dvd_r" in mediaCompatibility) or
            (not "optical_dvd_plus_r" in mediaCompatibility)):
            raise common.BurnerException("Device %s is not a CD/DVD "
                                         "burner" % self.device)
        ready = False
        while not ready:
            if not device.Get("", "DeviceIsOpticalDisc"):
                self.logger.info("Burning %s for %s. Please insert "
                                 "a blank disk in drive %s" % 
                                 (self.isoToBurn, self.isoCommitter,
                                  self.device))
                while not device.Get("", "DeviceIsOpticalDisc"):
                    time.sleep(1)
            if device.Get("", "OpticalDiscIsBlank"):
                self.logger.info("Blank disc detected in drive.")
                ready = True
            else:
                self.logger.warning("Inserted disk cannot be burnt."
                                    "Please change it.")
                while device.Get("", "DeviceIsOpticalDisc"):
                    time.sleep(1)
        return # Good device inserted

    def __waitForDiscHal(self, systemBus):
        """Waits for the disc to be inserted using HAL.
        
        Raises dbus.exceptions.DBusException or common.BurnerException
        in case of error.
        """
        proxy = systemBus.get_object("org.freedesktop.Hal", 
                                     "/org/freedesktop/Hal/Manager")
        manager = dbus.Interface(proxy, "org.freedesktop.Hal.Manager")
        # First check: FreeBSD requires a SCSI address x,y,z for CAM
        objectPaths = manager.FindDeviceStringMatch("block.freebsd.cam_path",
                                                    self.device)
        if objectPaths:
            # We are under FreeBSD
            objectPath = objectPaths[0]
            isCAMPath = True
        else:
            isCAMPath = False
            objectPaths = manager.FindDeviceStringMatch("block.device",
                                                        self.device)
            if not objectPaths:
                raise common.BurnerException("Device %s not in HAL database" %
                                             self.device)
            # We only like names containing "storage_serial" because they
            # are persistent
            for p in objectPaths:
                if "storage_serial" in p:
                    objectPath = p
                    break
            if not objectPath:
                raise common.BurnerException("Cannot find a suitable device "
                                             "for %s" % self.device)
        device = systemBus.get_object("org.freedesktop.Hal", objectPath)
        interface = dbus.Interface(device, "org.freedesktop.Hal.Device")
        if isCAMPath:
            # We need the actual device file
            deviceFile = interface.GetProperty("block.device")
        else:
            deviceFile = self.device
        if interface.GetProperty("info.category") != "storage.cdrom":
            raise common.BurnerException("Device %s is not a CD/DVD drive" %
                                         deviceFile)
        if ((not interface.GetProperty("storage.cdrom.cdr")) and
            (not interface.GetProperty("storage.cdrom.dvdr"))):
            raise common.BurnerException("Device %s is not a burner" % 
                                         deviceFile)
        ready = False
        p = "storage.removable.media_available"
        while not ready:
            if not interface.GetProperty(p):
                self.logger.info("Burning %s for %s. Please insert "
                                 "a blank disk in drive %s" % 
                                 (self.isoToBurn, self.isoCommitter,
                                  deviceFile))
                while not interface.GetProperty(p):
                    time.sleep(1)
            # We look for device paths containing the word "empty"
            objectPaths = manager.FindDeviceStringMatch("block.device",
                                                        deviceFile)
            for path in objectPaths:
                if "empty" in path:
                    ready = True
                    break
            if not ready:
                self.logger.warning("Inserted disk cannot be burnt. "
                                    "Please change it.")
                while interface.GetProperty(p):
                    time.sleep(1)
        self.logger.info("Blank disc detected in drive.")
        return # Good device inserted

    def __waitForDisc(self):
        """Waits for the disc to be inserted.
        
        If the device was specified, and dbus and udisks are reachable,
        automatically returns when the disc has been inserted. Otherwise,
        just prompts the user.
        """
        if self.device is not None:
            try:
                systemBus = dbus.SystemBus()
                names = systemBus.list_names()
                if "org.freedesktop.UDisks" in names:
                    return self.__waitForDiscUDisks(systemBus)
                elif "org.freedesktop.Hal" in names:
                    return self.__waitForDiscHal(systemBus)
            except dbus.exceptions.DBusException, e:
                self.logger.error(e)
            except common.BurnerException, e:
                self.logger.error(e)
        # If we got here, either we don't have dbus, or something went wrong.
        # We can just prompt the user.
        self.logger.info("Burning %s for %s. "
                         "Please insert disc and press ENTER" % \
                         (self.isoToBurn, self.isoCommitter))
        sys.stdin.readline()

    def live(self):
        """Waits for jobs and does them."""
        while not self.quitting:
            self.logger.info("Waiting for server request...")
            self.tcpServer.handle_request()
            if self.isoToBurn:
                # Burn!
                self.__waitForDisc()
                a = os.system(self.burnCmd % os.path.join(self.isoDirectory,
                                                          self.isoToBurn))
                try:
                    connection = self.__connectToServer()
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
            connection = self.__connectToServer()
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



############
def BurnerMain():
    """Main"""
    global burner
    # Cmd-line arguments
    parser = optparse.OptionParser()
    # Default values
    parser.set_defaults(server="127.0.0.1",
                        directory=".",
                        port=1235,
                        speed=4,
                        serverport=1234)
    parser.add_option("-n", "--name", dest="name", help="sets the burner name")
    parser.add_option("-d", "--dir", dest="directory",
                      help="specifies the directory containing the isos")
    parser.add_option("-D", "--device", dest="device",
                      help="specifies the burner device (overridden by -c)")
    parser.add_option("-S", "--speed", dest="speed", type="int",
                      help="specifies the burning speed (overridden by -c)")
    parser.add_option("-c", "--cmd", dest="command",
                      help="specifies the command to burn an iso named %s "
                      "(overrides -D and -S")
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
        if ((opts.command is None) and 
            ((opts.device is None) or (opts.speed is None))):
                sys.stderr.write("Please specify the speed and device "
                                 "(options -S and -D) or the burn command "
                                 "(option -c)\n")
                sys.exit(1)
        if opts.name is None:
            opts.name = socket.gethostname()
            if not opts.name:
                sys.stderr.write("Please specify the burner name "
                                 "(option -n)\n")
                sys.exit(1)
            if opts.device is not None:
                opts.name = "%s-%s" % (opts.name, opts.device)
        burner = CustomBurnerClient(opts.name, opts.directory,
                                    opts.port, opts.server, opts.serverport)
        if opts.command:
            burner.forceBurnCommand(opts.command)
        if opts.device is not None: # There is a default value for opts.speed
            burner.setBurnParameters(opts.device, opts.speed)
    except socket.error, e:
        # This may occur during server start
        sys.stderr.write("Socket error: %s\n" % str(e))
        sys.exit(-1)
    try:
        burner.live()
    except KeyboardInterrupt:
        # User killed this application, but the server is still running.
        burner.sayGoodbye()
