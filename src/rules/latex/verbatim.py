# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2005
"""
Dependency analysis for package 'verbatim' in Rubber.
"""

from os.path import basename
import rubber
from rubber import *

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		self.env = doc.env
		doc.add_hook("verbatiminput", self.input)

	def input (self, dict):
		if not dict["arg"]:
			return 0
		file = dict["arg"]
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.sources[file] = DependLeaf(self.env, file, loc=dict["pos"])
