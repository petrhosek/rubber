# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Extraction of bounding box information from gzipped PostScript figures.
"""

from rubber import _, msg
from rubber import *

from gzip import GzipFile
import re

re_bbox = re.compile("%[%\w]*BoundingBox:")

class Dep (Depend):
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		Depend.__init__(self, env, [target], {source: leaf})
		self.env = env
		self.source = source
		self.target = target

	def run (self):
		"""
		This method reads the source file (which is supposed to be a
		gzip-compressed PostScript file) until it finds a line that contains a
		bounding box indication. Then it creates the target file with this
		single line.
		"""
		msg.progress(_("extracting bounding box from %s") % self.source)
		source = GzipFile(self.source)
		line = source.readline()
		while line != "":
			if re_bbox.match(line):
				target = open(self.target, "w")
				target.write(line)
				target.close()
				return 0
			line = source.readline()
		source.close()
		msg.error(_("no bounding box was found in %s!") % self.source)
		return 1

def convert (source, target, env, vars):
	return Dep(env, target, source)
