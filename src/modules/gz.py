# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004
"""
Gzipping the output of Rubber.
"""

from gzip import GzipFile

import rubber
from rubber import _
from rubber.util import *

class Module (Depend, rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		self.doc = env.final.prods[0]
		self.gz = self.doc + ".gz"
		Depend.__init__(self, [self.gz], { self.doc: env.final }, env.msg)
		env.final = self
		self.options = []

	def run (self):
		self.msg(0, _("compressing %s...") % self.doc)
		out = GzipFile(self.gz, 'w')
		file = open(self.doc)
		out.write(file.read())
		file.close()
		out.close()
		return 0
