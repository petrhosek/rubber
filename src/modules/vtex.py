# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2003
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
			env.conf.latex = "vlatexp"
			env.out_ext = ".ps"
			env.final_file = env.src_base + ".ps"
		else:
			env.conf.latex = "vlatex"
			env.out_ext = ".pdf"
			env.final_file = env.src_base + ".pdf"
		env.conf.cmdline = ["-n1", "@latex", "%s"]
