# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2005
"""
PDF generation through dvipdfm with Rubber.
"""

import sys
from os.path import *

import rubber
from rubber import _
from rubber.util import *

class Module (Depend, rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		self.msg = env.msg
		if env.final.prods[0][-4:] != ".dvi":
			self.msg(0, _("I can't use dvipdfm when not producing a DVI"))
			sys.exit(2)
		self.dvi = env.final.prods[0]
		self.pdf = self.dvi[:-3] + "pdf"
		Depend.__init__(self, [self.pdf], { self.dvi: env.final }, env.msg)
		env.final = self
		self.options = []

	def run (self):
		self.msg(0, _("running dvipdfm on %s...") % self.dvi)
		cmd = ["dvipdfm"]
		for opt in self.env.conf.paper:
			cmd.extend(["-p", opt])
		cmd.extend(self.options + ["-o", self.pdf, self.dvi])
		if self.env.execute(cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

	def command (self, cmd, args):
		if cmd == "options":
			self.options.extend(args)
