# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2006
"""
Compressing the output of Rubber with bzip2.
"""

from bz2 import BZ2File

import rubber
from rubber import _, msg
from rubber import *
from rubber.depend import Node

class Dep (Node):
	def run (self):
		msg.progress(_("compressing %s") % self.sources[0])
		out = BZ2File(self.products[0], 'w')
		file = open(self.sources[0])
		out.write(file.read())
		file.close()
		out.close()
		return True

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		file = doc.env.final.products[0]
		bz2 = Dep(doc.env.depends, [file + ".bz2"], [file])
		doc.env.final = bz2
