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
		env.process.source_building = self.make
		env.process.src_ext = ".tex"
		env.process.cleaning_process.append(self.clean)

	def make (self):
		"""
		Weave the CWEB source into the LaTeX source.
		"""
		if not self.run_needed():
			return 0
		self.env.message(0, _("weaving %s.w...") % self.env.process.src_pbase)
		self.env.process.execute(["cweave", self.env.process.src_pbase])

	def run_needed (self):
		"""
		Check if weaving is necessary.
		"""
		pbase = self.env.process.src_pbase
		if not exists(pbase + ".tex"):
			self.env.message(2, _("the LaTeX source does not exist"))
			return 1
		if getmtime(pbase + ".tex") < getmtime(pbase + ".w"):
			self.env.message(2, _("the CWEB source was modified"))
			return 1
		self.env.message(2, _("the LaTeX source is up to date"))
		return 0

	def clean (self):
		"""
		Remove the LaTeX source and the other files produced by cweave.
		"""
		self.env.process.remove_suffixes([".tex", ".scn", ".idx"])
