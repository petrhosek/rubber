# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
CWEB support for Rubber.

This module handles CWEB by weaving the source file into the LaTeX source when
needed.
"""

from os.path import *

import rubber, rubber.util
from rubber import _

class Dep (rubber.util.Depend):
	def __init__ (self, source, target, env):
		leaf = rubber.util.DependLeaf([source])
		rubber.util.Depend.__init__(self, [target], { source: leaf })
		self.env = env
		self.source = source
		self.cmd = ["cweave", source, target]

	def run (self):
		self.env.msg(0, _("weaving %s...") % self.source)
		if self.env.execute(self.cmd):
			self.env.msg(0, _("weaving failed"))
			return 1
		return 0
		

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		if env.src_ext == ".w":
			env.source_building = self.make
			env.src_ext = ".tex"
		env.convert.add_rule("(.*)\\.tex$", "\\1.w", "cweb")

	def make (self):
		"""
		Weave the CWEB source into the LaTeX source.
		"""
		if not self.run_needed():
			return 0
		self.env.msg(0, _("weaving %s.w...") % self.env.src_pbase)
		if self.env.execute(["cweave", self.env.src_pbase]):
			self.env.msg(0, _("weaving failed"))
			return 1
		return 0

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

	def convert (self, source, target, env):
		"""
		Return a dependency node for the given target and the given source
		file names.
		"""
		return Dep(source, target, env)
