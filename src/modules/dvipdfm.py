# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
"""
PDF generation through dvipdfm with Rubber.
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
			self.msg(0, _("I can't use dvipdfm when not producing a DVI"))
			sys.exit(2)
		if env.output_processing:
			self.msg(0, _("there is already a post-processor registered"))
			sys.exit(2)
		env.output_processing = self.run
		env.final_file = env.src_base + ".pdf"
		self.options = []

	def run (self):
		"""
		Run dvipdfm if needed.
		"""
		if not self.run_needed():
			return 0
		self.msg(0, _("running dvipdfm on %s...") %
				(self.env.src_base + ".dvi"))
		cmd = ["dvipdfm"] + self.options + [
			"-o", self.env.src_base + ".pdf", self.env.src_base + ".dvi"]
		for opt in self.env.conf.paper:
			cmd.extend(["-p", opt])
		if self.env.execute(cmd):
			self.env.msg(0, _("the operation failed"))
			return 1
		return 0

	def run_needed (self):
		"""
		Check if running dvipdfm is needed.
		"""
		ps = self.env.src_base + ".pdf"
		if not exists(ps):
			self.msg(3, _("the PDF file doesn't exist"))
			return 1
		if getmtime(ps) < getmtime(self.env.src_base + ".dvi"):
			self.msg(3, _("the PDF file is older than the DVI"))
			return 1
		self.msg(3, _("running dvipdfm is not needed"))
		return 0

	def clean (self):
		self.env.remove_suffixes([".pdf"])

	def command (self, cmd, arg):
		if cmd == "options":
			self.options.extend(arg.split())
