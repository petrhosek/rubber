# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Conversion of many image formats into many others using the program 'convert'
from ImageMagick.
"""

from rubber import _
from rubber import *

class Dep (Depend):
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		Depend.__init__(self, env, [target], {source: leaf})
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["convert", source, target]

	def run (self):
		msg.progress(_("converting %s into %s") %
				(self.source, self.target))
		if self.env.execute(self.cmd):
			msg.error(_("conversion of %s into %s failed") %
					(self.source, self.target))
			return 1
		return 0

def convert (source, target, env, **args):
	if not prog_available("convert"):
		return None
	return Dep(env, target, source)
