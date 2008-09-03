# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Epsfig support for Rubber.

The package 'epsfig' is a somewhat deprecated interface to the graphics module
that simply provides a macro \\psfig with a keyval list argument to include
an EPS figure file.
"""

from rubber.util import parse_keyval

def setup (doc, context):
	global hook_includegraphics
	doc.do_module('graphics')
	_, hook_includegraphics = doc.hooks['includegraphics']
	# We proceed as if \epsfbox and \includegraphics were equivalent.
	doc.hook_macro('epsfbox', 'oa', hook_includegraphics)
	doc.hook_macro('epsffile', 'oa', hook_includegraphics)
	doc.hook_macro('epsfig', 'a', hook_epsfig)
	doc.hook_macro('psfig', 'a', hook_epsfig)

def hook_epsfig (loc, argument):
	# We just translate this into an equivalent call to \includegraphics.
	options = parse_keyval(argument)
	if 'file' not in options:
		return
	hook_includegraphics(loc, argument, options['file'])
