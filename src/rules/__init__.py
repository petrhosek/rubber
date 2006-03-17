# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2006
"""
Graphics file converters.

Each module in this package describes the operation of a particular external
utility that can be used to convert graphics files between formats. This root
module contains a Converter for the rules defined in the file "rules.ini".
"""

# Stop python 2.2 from calling "yield" statements syntax errors.
from __future__ import generators

import re
from os.path import *
from rubber import *
from rubber.version import moddir
from os.path import join

plugins = Plugins(__path__)
global std_rules
std_rules = Converter(plugins)
std_rules.read_ini(join(moddir, "rules.ini"))
