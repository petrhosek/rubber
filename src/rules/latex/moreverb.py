# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Dependency analysis and environment parsing for package 'moreverb' in Rubber.
"""

from os.path import basename
import rubber
from rubber import *

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		self.env = doc.env
		doc.add_hook("verbatimtabinput", self.input)
		doc.add_hook("listinginput", self.listinginput)
		for env in [
			"verbatimtab", "verbatimwrite", "boxedverbatim", "comment",
			"listing", "listing*", "listingcont", "listingcont*"]:
			doc.add_hook("begin{" + env + "}",
				lambda d, end="end{" + env + "}":
					doc.h_begin_verbatim(d, end=end))

	def input (self, dict):
		if not dict["arg"]:
			return 0
		file = dict["arg"]
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.sources[file] = DependLeaf(self.env, file, loc=dict["pos"])

	def listinginput (self, dict):
		if not dict["arg"]:
			return 0
		file = get_next_arg(dict)
		if not file:
			return 0
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.sources[file] = DependLeaf(self.env, file, loc=dict["pos"])
