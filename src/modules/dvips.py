# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2004
"""
PostScript generation through dvips with Rubber.
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
			self.msg(0, _("I can't use dvips when not producing a DVI"))
			sys.exit(2)
		self.dvi = env.final.prods[0]
		self.ps = self.dvi[:-3] + "ps"
		Depend.__init__(self, [self.ps], { self.dvi: env.final }, env.msg)
		env.final = self
		self.options = []

	def run (self):
		self.msg(0, _("running dvips on %s...") % self.dvi)
		cmd = ["dvips"] + self.options + ["-o", self.ps, self.dvi]
		for opt in self.env.conf.paper:
			cmd.extend(["-p", opt])
		if self.env.execute(cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

	def command (self, cmd, arg):
		if cmd == "options":
			self.options.extend(arg.split())
