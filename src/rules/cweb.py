# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
CWEB support for Rubber.

This module handles CWEB by weaving source files into the LaTeX source when
needed.
"""

import rubber
from rubber import _
from rubber import *
from rubber.depend import Node

class CWebDep (Node):
	def __init__ (self, env, target, source):
		tg_base = target[:-4]
		Node.__init__(self, env.depends,
			[target, tg_base + ".idx", tg_base + ".scn"], [source])
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
