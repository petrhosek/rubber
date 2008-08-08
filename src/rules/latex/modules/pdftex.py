# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
pdfLaTeX support for Rubber.

When this module is loaded with the otion 'dvi', the document is compiled to
DVI using pdfTeX.
"""

import sys
import rubber
from rubber import _, msg

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		self.env = doc.env
		self.mode = None
		doc.vars["program"] = "pdflatex"
		doc.vars["engine"] = "pdfTeX"
		if dict.has_key("opt") and dict["opt"] == "dvi":
			self.mode_dvi()
		else:
			self.mode_pdf()

	def mode_pdf (self):
		if self.mode == "pdf":
			return
		if self.env.final != self.doc and self.doc.products[0][-4:] != ".pdf":
			msg.error(_("there is already a post-processor registered"))
			return
		self.doc.reset_products([self.doc.target + ".pdf"])
		self.doc.cmdline = [
			opt for opt in self.doc.cmdline if opt != "\\pdfoutput=0"]
		self.mode = "pdf"

	def mode_dvi (self):
		if self.mode == "dvi":
			return
		if self.env.final != self.doc and self.doc.products[0][-4:] != ".dvi":
			msg.error(_("there is already a post-processor registered"))
			return
		self.doc.reset_products([self.doc.target + ".dvi"])
		self.doc.cmdline.insert(0, "\\pdfoutput=0")
		self.mode = "dvi"
