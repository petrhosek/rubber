# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
PostScript generation through dvips with Rubber.

This module has specific support for Omega: when the name of the main compiler
is "Omega" (instead of "TeX" for instance), then "odvips" is used instead of
"dvips".
"""

import sys
from os.path import *

import rubber
from rubber import _
from rubber import *

class Dep (Depend):
	def __init__ (self, doc, target, source, node):
		self.doc = doc
		self.env = doc.env
		self.source = source
		self.target = target
		Depend.__init__(self, doc.env, prods=[target], sources={source: node})
		self.options = []

	def run (self):
		if self.doc.conf.tex == "Omega":
			cmd = ["odvips"]
		else:
			cmd = ["dvips"]
		msg.progress(_("running %s on %s") % (cmd[0], self.source))
		for opt in self.doc.conf.paper:
			cmd.extend(["-t", opt])
		cmd.extend(self.options + ["-o", self.target, self.source])
		if self.env.execute(cmd):
			msg.error(0, _("%s failed on %s") % (cmd[0], self.source))
			return 1
		return 0

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		if doc.env.final.prods[0][-4:] != ".dvi":
			msg.error(_("I can't use dvips when not producing a DVI"))
			sys.exit(2)
		dvi = doc.env.final.prods[0]
		ps = dvi[:-3] + "ps"
		self.dep = Dep(doc, ps, dvi, doc.env.final)
		doc.env.final = self.dep

	def command (self, cmd, args):
		if cmd == "options":
			self.dep.options.extend(args)
