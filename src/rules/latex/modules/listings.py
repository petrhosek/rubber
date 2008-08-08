# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Dependency analysis and environment parsing for package 'listings' in Rubber.
"""

from os.path import basename
import rubber
from rubber import *

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		self.env = doc.env
		doc.hook_macro("lstinputlisting", "oa", self.input)
		doc.hook_macro("lstnewenvironment", "a", self.newenvironment)
		doc.hook_begin("lstlisting",
			lambda loc: doc.h_begin_verbatim(loc, env="lstlisting"))

	def input (self, loc, opt, file):
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.add_source(file)

	def newenvironment (self, loc, name):
		def func (loc):
			self.doc.h_begin_verbatim(loc, env=name)
		self.doc.hook_begin(name, func)
