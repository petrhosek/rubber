# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
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
from rubber.depend import Node

class Dep (Node):
	def __init__ (self, doc, target, source):
		Node.__init__(self, doc.env.depends, [target], [source])
		self.doc = doc
		self.env = doc.env
		self.source = source
		self.target = target
		self.options = []

	def run (self):
		if self.doc.vars["engine"] == "Omega":
			cmd = ["odvips"]
		else:
			cmd = ["dvips"]
		msg.progress(_("running %s on %s") % (cmd[0], self.source))
		for opt in self.doc.vars["paper"].split():
			cmd.extend(["-t", opt])
		cmd.extend(self.options + ["-o", self.target, self.source])
		if self.env.execute(cmd, kpse=1):
			msg.error(_("%s failed on %s") % (cmd[0], self.source))
			return False
		return True

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		if doc.env.final.products[0][-4:] != ".dvi":
			msg.error(_("I can't use dvips when not producing a DVI"))
			sys.exit(2)
		dvi = doc.env.final.products[0]
		ps = dvi[:-3] + "ps"
		self.dep = Dep(doc, ps, dvi)
		doc.env.final = self.dep

	def do_options (self, *args):
		self.dep.options.extend(args)
