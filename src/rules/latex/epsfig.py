# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2004
"""
Epsfig support for Rubber.

The package 'epsfig' is a somewhat deprecated interface to the graphics module
that simply provides a macro \\psfig with a keyval list argument to include
an EPS figure file.
"""

import rubber, rubber.util
import rubber.rules.latex.graphics

class Module (rubber.rules.latex.graphics.Module):
	def __init__ (self, doc, dict):
		"""
		This initialization method calls the one from module 'graphics', which
		registers its specific macros. This is not wrong: the epsfig package
		does that too.
		"""
		rubber.rules.latex.graphics.Module.__init__(self, doc, dict)
		doc.add_hook("epsfbox", self.includegraphics)
		doc.add_hook("epsffile", self.includegraphics)
		doc.add_hook("epsfig", self.epsfig)
		doc.add_hook("psfig", self.epsfig)

	def epsfig (self, dict):
		"""
		This macro is called when a \\psfig or \\epsfig macro is found. It
		mainly translates it into a call to \\includegraphics.
		"""
		arg = dict["arg"]
		if not arg:
			return
		opts = rubber.util.parse_keyval(arg)
		if not opts.has_key("file"):
			return
		fake = dict.copy()
		fake["arg"] = opts["file"]
		fake["opt"] = arg
		self.includegraphics(fake)
