# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2003
"""
pdfLaTeX support for Rubber.

When this module loaded with the otion 'dvi', the document is compiled to DVI
using pdfTeX.
"""

import rubber

class Module (rubber.Module):
	def __init__ (self, env, dict):
		env.conf.latex = "pdflatex"
		env.conf.tex = "pdfTeX"
		if dict.has_key("opt") and dict["opt"] == "dvi":
			env.conf.cmdline.insert(0, "\\pdfoutput=0")
		else:
			env.out_ext = ".pdf"
			env.final_file = env.src_base + ".pdf"
