# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
PostScript generation through dvips with Rubber.
"""

import sys
from os.path import *

import rubber
from rubber import _

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		self.msg = env.msg
		if env.out_ext != ".dvi":
			self.msg(0, _("I can't use dvips when not producing a DVI"))
			sys.exit(2)
		if env.output_processing:
			self.msg(0, _("there is already a post-processor registered"))
			sys.exit(2)
		env.output_processing = self.run

	def run (self):
		"""
		Run dvips if needed.
		"""
		if not self.run_needed():
			return 0
		self.msg(0, _("running dvips on %s...") %
				(self.env.src_base + ".dvi"))
		cmd = ["dvips", self.env.src_base + ".dvi",
			"-o", self.env.src_base + ".ps"]
		for opt in self.env.conf.paper:
			cmd.extend(["-t", opt])
		if self.env.execute(cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

	def run_needed (self):
		"""
		Check if running dvips is needed.
		"""
		ps = self.env.src_base + ".ps"
		if not exists(ps):
			self.msg(3, _("the PostScript file doesn't exist"))
			return 1
		if getmtime(ps) < getmtime(self.env.src_base + ".dvi"):
			self.msg(3, _("the PostScript file is older than the DVI"))
			return 1
		self.msg(3, _("running dvips is not needed"))
		return 0

	def clean (self):
		self.env.remove_suffixes([".ps"])
