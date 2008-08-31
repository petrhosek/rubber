# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
CWEB support for Rubber.

This module handles CWEB by weaving source files into the LaTeX source when
needed.
"""

from rubber.util import prog_available
from rubber.depend import Shell

def check (source, target, context):
	return prog_available('cweave')

def convert (source, target, context, set):
	base = target[:-4]
	return Shell(set,
		["cweave", source, target],
		[target, base + ".idx", base + ".scn"],
		[source])
