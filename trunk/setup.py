#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Custom Burner setup script
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

import os
import os.path
from distutils.core import setup

version_string = "0.5"

setup(name='custom-burner',
      version=version_string,
      description='A script that allows to burn CD/DVDs on multiple computers',
      author='Arrigo Marchiori',
      author_email='ardovm at yahoo dot it',
      url='http://custom-burner.berlios.de/',
      packages=['custom_burner', 'custom_burner.server'],
      scripts=['custom-burner-client', 'custom-burner-server'],
      data_files=[('share/doc/custom-burner-%s' % (version_string),
                   [os.path.join('doc', 'README.html'), 
                    os.path.join('doc', 'COPYING')])],
      )
