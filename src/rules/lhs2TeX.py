# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
Literate Haskell support for Rubber.

This module handles Literate Haskell by using the lhs2TeX processor to
pretty-print Haskell code in the source file when needed.
"""

import rubber
from rubber import _
from rubber import *

class LHSDep (Depend):
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		tg_base = target[:-4]
		Depend.__init__(self, env, prods=[target], sources={ source: leaf })
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["lhs2TeX", "--poly", source]

	def run (self):
		msg.progress(_("pretty-printing %s") % self.source)
		out = open(self.target, 'w')
		def w (line, file=out):
			file.write(line)
			file.flush()
		if self.env.execute(self.cmd, out=w):
			out.close()
			msg.error(_("pretty-printing of %s failed") % self.source)
			return 1
		out.close()
		return 0

def convert (source, target, env, vars):
	return LHSDep(env, target, source)
