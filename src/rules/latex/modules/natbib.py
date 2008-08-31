# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
"""
Natbib support for Rubber

This package handles the behaviour specific to natbib, i.e. the fact that an
extra compilation may be needed when using this package.
"""

import re

import rubber

re_rerun = re.compile("\(natbib\).*Rerun ")

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc

	def post_compile (self):
		for line in self.doc.log.lines:
			if re_rerun.match(line):
				self.doc.must_compile = 1
				return True
		return True
