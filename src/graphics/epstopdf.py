# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Conversion of EPS graphics into PDF.
"""

from rubber import _
from rubber.util import *

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source], env.msg)
		Depend.__init__(self, [target], {source: leaf}, env.msg)
		self.env = env
		self.source = source

		# The "env" is a hack because on some systems, the epstopdf executable
		# appears to be broken, which seems to make direct execution fail,
		# while "env" may be more clever.

		self.cmd = ["env", "epstopdf", "--outfile=" + target, source]

	def run (self):
		self.env.msg(0, _("converting %s to PDF...") % self.source)
		if self.env.execute(self.cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

def convert (source, target, env):
	return Dep(target, source, env)
