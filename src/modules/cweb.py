# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
CWEB support for Rubber.

This module handles CWEB by weaving the source file into the LaTeX source when
needed.
"""

from os.path import *

def _ (txt): return txt

class Module:
	def __init__ (self, env, dict):
		self.env = env
		env.source_building = self.make
		env.src_ext = ".tex"
		env.cleaning_process.append(self.clean)

	def make (self):
		"""
		Weave the CWEB source into the LaTeX source.
		"""
		if not self.run_needed():
			return 0
		self.env.msg(0, _("weaving %s.w...") % self.env.src_pbase)
		return self.env.execute(["cweave", self.env.src_pbase])

	def run_needed (self):
		"""
		Check if weaving is necessary.
		"""
		pbase = self.env.src_pbase
		if not exists(pbase + ".tex"):
			self.env.msg(2, _("the LaTeX source does not exist"))
			return 1
		if getmtime(pbase + ".tex") < getmtime(pbase + ".w"):
			self.env.msg(2, _("the CWEB source was modified"))
			return 1
		self.env.msg(2, _("the LaTeX source is up to date"))
		return 0

	def clean (self):
		"""
		Remove the LaTeX source and the other files produced by cweave.
		"""
		self.env.remove_suffixes([".tex", ".scn", ".idx"])
