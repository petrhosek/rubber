# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
VTeX support for Rubber.

This module specifies that the VTeX/Free compiler should be used. This
includes using "vlatex" of "vlatexp" instead of "latex" and knowing that this
produces a PDF or PostScript file directly. The PDF version is used by
default, switching to PS is possible by using the module option "ps".
"""

import rubber

class Module (rubber.Module):
	def __init__ (self, env, dict):
		env.conf.tex = "VTeX"
		if dict['opt'] == "ps":
			if env.final != env and env.prods[0][-4:] != ".ps":
				msg.error(_("there is already a post-processor registered"))
				sys.exit(2)
			env.conf.latex = "vlatexp"
			env.prods = [env.src_base + ".ps"]
		else:
			if env.final != env and env.prods[0][-4:] != ".pdf":
				msg.error(_("there is already a post-processor registered"))
				sys.exit(2)
			env.conf.latex = "vlatex"
			env.prods = [env.src_base + ".pdf"]
		env.conf.cmdline = ["-n1", "@latex", "%s"]
