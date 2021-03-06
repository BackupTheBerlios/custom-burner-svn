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

class Accumulator:
    """A FIFO queue disguised as a stream.

    This class is used to connect the logging subsystem to the user interface.
    """
    def __init__(self):
        """Constructor: initializes the FIFO."""
        self.__fifo = []

    def write(self, what):
        """Adds something to the FIFO."""
        self.__fifo.append(what.strip())

    def flush(self):
        """Does nothing: write() does everything we need."""
        pass

    def pop(self):
        """Returns the first element in the queue.

        Throws IndexError if the queue is empty."""
        return self.__fifo.pop(0)
