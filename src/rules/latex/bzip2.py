# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2006
"""
Compressing the output of Rubber with bzip2.
"""

from bz2 import BZ2File

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
		out = BZ2File(self.target, 'w')
		file = open(self.source)
		out.write(file.read())
		file.close()
		out.close()
		return 0

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		file = doc.env.final.prods[0]
		bz2 = Dep(doc.env, file + ".bz2", file, doc.env.final)
		doc.env.final = bz2
