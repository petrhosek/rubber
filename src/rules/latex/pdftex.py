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

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		doc.conf.latex = "pdflatex"
		doc.conf.tex = "pdfTeX"
		env = doc.env
		if dict.has_key("opt") and dict["opt"] == "dvi":
			if env.final != doc and doc.prods[0][-4:] != ".dvi":
				msg.error(_("there is already a post-processor registered"))
				sys.exit(2)
			doc.conf.cmdline.insert(0, "\\pdfoutput=0")
		else:
			if env.final != doc and doc.prods[0][-4:] != ".pdf":
				msg.error(_("there is already a post-processor registered"))
				sys.exit(2)
			doc.prods = [doc.src_base + ".pdf"]
