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
		doc.hook_macro("verbatimtabinput", "oa", self.verbatimtabinput)
		doc.hook_macro("listinginput", "oaa", self.listinginput)
		for env in [
			"verbatimtab", "verbatimwrite", "boxedverbatim", "comment",
			"listing", "listing*", "listingcont", "listingcont*"]:
			doc.hook_begin(env, lambda loc: doc.h_begin_verbatim(loc, env=env))

	def verbatimtabinput (self, loc, tabwidth, file):
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.add_source(file)

	def listinginput (self, loc, interval, start, file):
		if file.find("\\") < 0 and file.find("#") < 0:
			self.doc.add_source(file)
