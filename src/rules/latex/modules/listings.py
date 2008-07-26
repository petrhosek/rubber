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
		doc.add_hook("lstinputlisting", self.input)
		doc.add_hook("lstnewenvironment", self.newenvironment)
		doc.add_hook("begin{lstlisting}",
			lambda d: doc.h_begin_verbatim(d, end="end{lstlisting}"))

	def input (self, dict):
		if not dict["arg"]:
			return
		file = dict["arg"]
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.sources[file] = DependLeaf(self.env, file, loc=dict["pos"])

	def newenvironment (self, dict):
		if not dict["arg"]:
			return
		self.doc.add_hook("begin{" + dict["arg"] + "}",
			lambda d, end="end{" + dict["arg"] + "}":
				self.doc.h_begin_verbatim(d, end=end))
