# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Metapost support for Rubber.

For now, this is just a minimalistic support. It should be extended to parse
source files for dependencies, and so on. What about a Rubber for Metapost?
"""

from rubber.util import *

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source])
		Depend.__init__(self, [target], {source: leaf})
		self.env = env
		self.base = source[:-3]
		self.cmd = ["mpost", "--interaction=batchmode", self.base]

	def run (self):
		self.env.message(0, "running Metapost on %s.mp..." % self.base)
		self.env.process.execute(self.cmd)
		# This creates a log file that has the same aspect as TeX logs.
		log = open(self.base + ".log")
		line = log.readline()
		while line != "":
			if line[0] == "!":
				self.env.message(0,
"Metapost compilation failed (see %s.log for details)." % self.base)
				log.close()
				return 1
			line = log.readline()
		log.close()
		return 0

files = {}

def convert (source, target, env):
	if files.has_key(source):
		files[source].prods.append(target)
	else:
		files[source] = Dep(target, source, env)
	return files[source]
