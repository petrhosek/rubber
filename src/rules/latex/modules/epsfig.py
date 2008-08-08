# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Epsfig support for Rubber.

The package 'epsfig' is a somewhat deprecated interface to the graphics module
that simply provides a macro \\psfig with a keyval list argument to include
an EPS figure file.
"""

import rubber, rubber.util
import rubber.rules.latex.modules.graphics

class Module (rubber.rules.latex.modules.graphics.Module):
	def __init__ (self, doc, dict):
		"""
		This initialization method calls the one from module 'graphics', which
		registers its specific macros. This is not wrong: the epsfig package
		does that too.
		"""
		rubber.rules.latex.modules.graphics.Module.__init__(self, doc, dict)
		doc.hook_macro("epsfbox", "oa", self.includegraphics)
		doc.hook_macro("epsffile", "oa", self.includegraphics)
		doc.hook_macro("epsfig", "a", self.epsfig)
		doc.hook_macro("psfig", "a", self.epsfig)

	def epsfig (self, loc, arg):
		"""
		This macro is called when a \\psfig or \\epsfig macro is found. It
		mainly translates it into a call to \\includegraphics.
		"""
		opts = rubber.util.parse_keyval(arg)
		if not opts.has_key("file"):
			return
		self.includegraphics(loc, arg, opts["file"])
