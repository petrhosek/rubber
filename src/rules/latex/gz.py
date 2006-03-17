# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2006
"""
Gzipping the output of Rubber.
"""

from gzip import GzipFile

import rubber
from rubber import _, msg
from rubber import *

class Dep (Depend):
	def __init__ (self, env, target, source, node):
		self.env = env
		self.source = source
		self.target = target
		Depend.__init__(self, env, prods=[target], sources={source: node})

	def run (self):
		msg.progress(_("compressing %s") % self.source)
		out = GzipFile(self.target, 'w')
		file = open(self.source)
		out.write(file.read())
		file.close()
		out.close()
		return 0

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		file = doc.env.final.prods[0]
		gz = Dep(doc.env, file + ".gz", file, doc.env.final)
		doc.env.final = gz
