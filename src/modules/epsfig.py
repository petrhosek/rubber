# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2004
"""
Epsfig support for Rubber.

The package 'epsfig' is a somewhat deprecated interface to the graphics module
that simply provides a macro \\psfig with a keyval list argument to include
an EPS figure file.
"""

import rubber, rubber.util
import rubber.modules.graphics

class Module (rubber.modules.graphics.Module):
	def __init__ (self, env, dict):
		"""
		This initialization method calls the one from module 'graphics', which
		registers its specific macros. This is not wrong: the epsfig package
		does that too.
		"""
		rubber.modules.graphics.Module.__init__(self, env, dict)
		env.add_hook("epsfbox", self.includegraphics)
		env.add_hook("epsffile", self.includegraphics)
		env.add_hook("epsfig", self.epsfig)
		env.add_hook("psfig", self.epsfig)

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
		self.includegraphics({ "arg": opts["file"], "opt": arg })
