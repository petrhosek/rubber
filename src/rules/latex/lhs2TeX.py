# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
Literate Haskell support for Rubber.

This module handles Literate Haskell by using the lhs2TeX processor to
pretty-print Haskell code in the source file when needed.
"""

from os.path import *

import rubber
from rubber import _
from rubber import *
from rubber.rules.lhs2TeX import LHSDep

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		doc.env.pkg_rules.add_rule("(.*)\\.tex$", "\\1.lhs", 0, "lhs2TeX")
		self.style = "--poly"

	def command (self, cmd, args):
		if cmd == "style":
			if len(args) > 0:
				self.style = "--" + args[0]

	def convert (self, source, target, env):
		"""
		Return a dependency node for the given target and the given source
		file names.
		"""
		return LHSDep(env, target, source)
