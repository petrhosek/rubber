# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2006
"""
Compressing the output of Rubber with bzip2.
"""

from bz2 import BZ2File

from rubber import _, msg
from rubber.depend import Node

class Bzip2Dep (Node):
	def __init__ (self, set, target, source):
		Node.__init__(self, set, [target], [source])
	def run (self):
		msg.progress(_("compressing %s") % self.sources[0])
		out = BZ2File(self.products[0], 'w')
		file = open(self.sources[0])
		out.write(file.read())
		file.close()
		out.close()
		return True
