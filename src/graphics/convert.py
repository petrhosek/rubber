# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Conversion of many image formats into many others using the program 'convert'
from ImageMagick.
"""

from rubber import _
from rubber.util import *

# Useful formats that 'convert' can produce:

outputs = ["epdf", "eps", "pdf", "png", "ps"]

# Useful formats that 'convert' can read:

inputs = [
	"bmp", "eps", "epdf", "gif", "jbg", "jbig", "jpeg", "jpg", "pct", "pcx",
	"pdf", "pgm", "pict", "png", "pnm", "ppm", "ps", "tga", "tif", "tiff",
	"wmf", "xbm", "xcf", "xpm"]

# A set of rules we actually don't want:

avoid = { "pdf": ["png"], "png": ["pdf"] }

# A function to update the translation table with these:

def update_rules (rules):
	for o in outputs:
		expr = "(.*)\\." + o + "$"
		if rules.has_key(expr):
			table = rules[expr]
		else:
			table = {}
			rules[expr] = table
		for i in inputs:
			if o == i or (avoid.has_key(o) and i in avoid[o]):
				continue
			expr = "\\1." + i
			if table.has_key(expr):
				table[expr].insert(0, "convert")
			else:
				table[expr] = ["convert"]

# The actual dependency node:

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source])
		Depend.__init__(self, [target], {source: leaf})
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["convert", source, target]

	def run (self):
		self.env.msg(0, _("converting %s into %s...") %
				(self.source, self.target))
		if self.env.execute(self.cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

def convert (source, target, env):
	return Dep(target, source, env)
