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
		if env.conf.tex == "Omega":
			self.cmd = "odvips"
		else:
			self.cmd = "dvips"
		self.options = []

	def run (self):
		self.msg(0, _("running %s on %s...") % (self.cmd, self.dvi))
		cmd = [self.cmd]
		for opt in self.env.conf.paper:
			cmd.extend(["-t", opt])
		cmd.extend(self.options + ["-o", self.ps, self.dvi])
		if self.env.execute(cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

	def command (self, cmd, args):
		if cmd == "options":
			self.options.extend(args)
