# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
pdfLaTeX support for Rubber.

When this module loaded with the otion 'dvi', the document is compiled to DVI
using pdfTeX.
"""

import sys
import rubber
from rubber import _, msg

class Module (rubber.Module):
	def __init__ (self, env, dict):
		env.conf.latex = "pdflatex"
		env.conf.tex = "pdfTeX"
		if dict.has_key("opt") and dict["opt"] == "dvi":
			if env.final != env and env.prods[0][-4:] != ".dvi":
				msg.error(_("there is already a post-processor registered"))
				sys.exit(2)
			env.conf.cmdline.insert(0, "\\pdfoutput=0")
		else:
			if env.final != env and env.prods[0][-4:] != ".pdf":
				msg.error(_("there is already a post-processor registered"))
				sys.exit(2)
			env.prods = [env.src_base + ".pdf"]
