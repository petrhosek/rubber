# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Conversion of many image formats into many others using the program 'convert'
from ImageMagick.
"""

from rubber import _
from rubber import *

# Useful formats that 'convert' can produce, with a "position" to compute
# their distance to other formats:

outputs = [
	("epdf", 1), ("eps", 1), ("pdf", 1), ("ps", 1),
	("png", 10),
	("jpg", 15), ("jpeg", 15)]

# Useful formats that 'convert' can read, also with positions:

inputs = [
	("eps", 1), ("epdf", 1), ("pdf", 1), ("ps", 2), ("wmf", 3),
	("bmp", 10), ("gif", 10), ("jbg", 10), ("jbig", 10), ("pct", 10),
	("pcx", 10), ("pgm", 10), ("pict", 10), ("png", 10), ("pnm", 10),
	("ppm", 10), ("tga", 10), ("tif", 10), ("tiff", 10), ("xbm", 10),
	("xcf", 10), ("xpm", 10),
	("jpeg", 15), ("jpg", 15) ]

# A function to update the translation table with these:

def update_rules (rules):
	for (o,po) in outputs:
		expr = "(.*)\\." + o + "$"
		if rules.has_key(expr):
			table = rules[expr]
		else:
			table = {}
			rules[expr] = table
		for (i,pi) in inputs:
			if o == i:
				continue
			expr = "\\1." + i
			weight = abs(pi - po) + 2
			if table.has_key(expr):
				table[expr].insert(0, (weight, "convert"))
			else:
				table[expr] = [(weight, "convert")]

# The actual dependency node:

class Dep (Depend):
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		Depend.__init__(self, env, [target], {source: leaf})
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["convert", source, target]

	def run (self):
		msg.progress(_("converting %s into %s") %
				(self.source, self.target))
		if self.env.execute(self.cmd):
			msg.error(_("conversion of %s into %s failed") %
					(self.source, self.target))
			return 1
		return 0

def convert (source, target, env):
	if not prog_available("convert"):
		return None
	return Dep(env, target, source)
