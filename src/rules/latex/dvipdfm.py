# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2005
"""
PDF generation through dvipdfm with Rubber.
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
		msg.progress(_("running dvipdfm on %s") % self.source)
		cmd = ["dvipdfm"]
		for opt in self.doc.conf.paper:
			cmd.extend(["-p", opt])
		cmd.extend(self.options + ["-o", self.target, self.source])
		if self.env.execute(cmd):
			msg.error(0, _("dvipdfm failed on %s") % self.source)
			return 1
		return 0

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		if doc.env.final.prods[0][-4:] != ".dvi":
			msg.error(_("I can't use dvipdfm when not producing a DVI"))
			sys.exit(2)
		dvi = doc.env.final.prods[0]
		pdf = dvi[:-3] + "pdf"
		self.dep = Dep(doc, pdf, dvi, doc.env.final)
		doc.env.final = self.dep

	def command (self, cmd, args):
		if cmd == "options":
			self.dep.options.extend(args)
