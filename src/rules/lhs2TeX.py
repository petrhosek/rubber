# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
Literate Haskell support for Rubber.

This module handles Literate Haskell by using the lhs2TeX processor to
pretty-print Haskell code in the source file when needed.
"""

from subprocess import Popen
from rubber.util import prog_available
from rubber.depend import Node

def check (source, target, context):
	return prog_available('lhs2tex')

class LHSDep (Node):
	def __init__ (self, set, target, source):
		Node.__init__(self, set, [target], [source])
		self.source = source
		self.target = target

	def run (self):
		msg.progress(_("pretty-printing %s") % self.source)
		output = open(self.target, 'w')
		process = Popen(['lhs2tex', '--poly', self.source], stdout=output)
		if process.wait() != 0:
			msg.error(_("pretty-printing of %s failed") % self.source)
			return False
		output.close()
		return True

def convert (source, target, context, set):
	return LHSDep(set, target, source)
