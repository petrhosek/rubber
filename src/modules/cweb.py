# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
CWEB support for Rubber.

This module handles CWEB by weaving the source file into the LaTeX source when
needed.
"""

from os.path import *

import rubber
from rubber import _, msg
from rubber.util import *

class Dep (Depend):
	def __init__ (self, source, target, env):
		leaf = DependLeaf([source])
		tg_base = target[:-4]
		Depend.__init__(self,
			[target, tg_base + ".idx", tg_base + ".scn"], { source: leaf },
			msg)
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["cweave", source, target]

	def run (self):
		msg.progress(_("weaving %s") % self.source)
		if self.env.execute(self.cmd):
			msg.error(_("weaving of %s failed") % self.source)
			return 1
		self.env.process(self.target)
		return 0


class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		if env.src_ext == ".w":
			self.clean_tex = 1
			env.source_building = self.make
			env.src_ext = ".tex"
		else:
			self.clean_tex = 0
		env.convert.add_rule("(.*)\\.tex$", "\\1.w", 0, "cweb")

	def make (self):
		"""
		Weave the CWEB source into the LaTeX source.
		"""
		if not self.run_needed():
			return 0
		msg.progress(_("weaving %s.w") % self.env.src_pbase)
		if self.env.execute(["cweave", self.env.src_pbase]):
			msg.error(_("weaving of %s.w failed") % self.env.src_pbase)
			return 1
		return 0

	def run_needed (self):
		"""
		Check if weaving is necessary.
		"""
		pbase = self.env.src_pbase
		if not exists(pbase + ".tex"):
			msg.log(_("the LaTeX source does not exist"))
			return 1
		if getmtime(pbase + ".tex") < getmtime(pbase + ".w"):
			msg.log(_("the CWEB source was modified"))
			return 1
		msg.log(_("the LaTeX source is up to date"))
		return 0

	def clean (self):
		"""
		Remove the LaTeX source and the other files produced by cweave.
		"""
		if self.clean_tex:
			self.env.remove_suffixes([".tex", ".scn", ".idx"])

	def convert (self, source, target, env):
		"""
		Return a dependency node for the given target and the given source
		file names.
		"""
		return Dep(source, target, env)
