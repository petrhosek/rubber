# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Conversion of JPEG graphics into PostScript.
"""

from rubber import _, msg
from rubber.util import *

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source])
		Depend.__init__(self, [target], {source: leaf})
		self.env = env
		self.source = source
		self.cmd = ["jpeg2ps", "-o", target, source]

	def run (self):
		msg.progress(_("converting %s to EPS") % self.source)
		if self.env.execute(self.cmd):
			msg.error(_("conversion of %s to EPS failed") % self.source)
			return 1
		return 0

def convert (source, target, env):
	if not prog_available("jpeg2ps"):
		return None
	return Dep(target, source, env)
