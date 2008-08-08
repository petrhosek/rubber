# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Dependency analysis and environment parsing for package 'verbatim' in Rubber.
"""

from os.path import basename
import rubber
from rubber import *

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		self.env = doc.env
		doc.hook_macro("verbatiminput", "a", self.input)
		doc.hook_begin("comment",
			lambda loc: doc.h_begin_verbatim(loc, env="comment"))

	def input (self, loc, file):
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.add_source(file)
