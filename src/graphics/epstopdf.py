# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Conversion of EPS graphics into PDF.
"""

from rubber.util import *

def _ (txt): return txt

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source])
		Depend.__init__(self, [target], {source: leaf})
		self.env = env
		self.source = source
		self.cmd = ["epstopdf", "--outfile=" + target, source]

	def run (self):
		self.env.msg(0, _("converting %s to PDF...") % self.source)
		self.env.execute(self.cmd)
		# FIXME: we should check that the conversion worked
		return 0

def convert (source, target, env):
	return Dep(target, source, env)
