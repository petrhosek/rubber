# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Conversion of JPEG graphics into PostScript.
"""

from rubber import _
from rubber.util import *

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source], env.msg)
		Depend.__init__(self, [target], {source: leaf}, env.msg)
		self.env = env
		self.source = source
		self.cmd = ["jpeg2ps", "-o", target, source]

	def run (self):
		self.env.msg(0, _("converting %s to EPS...") % self.source)
		if self.env.execute(self.cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

def convert (source, target, env):
	if not prog_available("jpeg2ps"):
		return None
	return Dep(target, source, env)
