# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2003
"""
pfdLaTeX support for Rubber.
"""

import rubber

class Module (rubber.Module):
	def __init__ (self, env, dict):
		env.conf.latex = "pdflatex"
		env.conf.tex = "pdfTeX"
		env.out_ext = ".pdf"
