# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Conversion of EPS graphics into PDF.
"""

from rubber import _, msg
from rubber import *

class Dep (Depend):
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		Depend.__init__(self, env, [target], {source: leaf})
		self.env = env
		self.source = source

		# The "env" is a hack because on some systems, the epstopdf executable
		# appears to be broken, which seems to make direct execution fail,
		# while "env" may be more clever.

		self.cmd = ["env", "epstopdf", "--outfile=" + target, source]

	def run (self):
		msg.progress(_("converting %s to PDF") % self.source)
		if self.env.execute(self.cmd):
			msg.error(_("conversion of %s into PDF failed") % self.source)
			return 1
		return 0

def convert (source, target, env, vars):
	if not prog_available("epstopdf"):
		return None
	return Dep(env, target, source)
