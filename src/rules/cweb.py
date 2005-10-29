# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
CWEB support for Rubber.

This module handles CWEB by weaving source files into the LaTeX source when
needed.
"""

import rubber
from rubber import _
from rubber import *

class CWebDep (Depend):
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		tg_base = target[:-4]
		Depend.__init__(self, env,
			prods=[target, tg_base + ".idx", tg_base + ".scn"],
			sources={ source: leaf })
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["cweave", source, target]

	def run (self):
		msg.progress(_("weaving %s") % self.source)
		if self.env.execute(self.cmd):
			msg.error(_("weaving of %s failed") % self.source)
			return 1
		return 0


def check (vars, env):
	return vars
def convert (vars, env):
	return CWebDep(vars["source"], vars["target"], env)
