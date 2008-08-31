# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2006
"""
Gzipping the output of Rubber.
"""

from gzip import GzipFile

from rubber import _, msg
from rubber.depend import Node

class GzipDep (Node):
	def __init__ (self, set, target, source):
		Node.__init__(self, set, [target], [source])
	def run (self):
		msg.progress(_("compressing %s") % self.sources[0])
		out = GzipFile(self.products[0], 'w')
		file = open(self.sources[0])
		out.write(file.read())
		file.close()
		out.close()
		return True
