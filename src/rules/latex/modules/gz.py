# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2006
"""
Gzipping the output of Rubber.
"""

from gzip import GzipFile

import rubber
from rubber import _, msg
from rubber import *
from rubber.depend import Node

class Dep (Node):
	def __init__ (self, env, target, source):
		Node.__init__(self, env.depends, [target], [source])
		self.env = env
		self.source = source
		self.target = target

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
		file = doc.env.final.products[0]
		gz = Dep(doc.env, file + ".gz", file)
		doc.env.final = gz
