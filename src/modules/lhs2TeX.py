# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
Literate Haskell support for Rubber.

This module handles Literate Haskell by using the lhs2TeX processor to
pretty-print Haskell code in the source file when needed.
"""

from os.path import *

import rubber
from rubber import _
from rubber.util import *

class Dep (Depend):
	def __init__ (self, source, target, env):
		leaf = DependLeaf([source], env.msg)
		tg_base = target[:-4]
		Depend.__init__(self, [target], { source: leaf }, env.msg)
		self.env = env
		self.source = source
		self.target = target
		self.cmd = ["lhs2TeX", "-math", source]

	def run (self):
		self.env.msg(0, _("pretty-printing %s...") % self.source)
		out = open(target, 'w')
		def w (line, file=out):
		  file.write(line)
		  file.flush()
		if self.env.execute(self.cmd, out=w):
			out.close()
			self.env.msg(0, _("processing failed"))
			return 1
		out.close()
		self.env.process(self.target)
		return 0


class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		if env.src_ext == ".lhs":
			self.clean_tex = 1
			env.source_building = self.make
			env.src_ext = ".tex"
		else:
			self.clean_tex = 0
		env.convert.add_rule("(.*)\\.tex$", "\\1.lhs", "lhs2TeX")
		self.style = "-math"

	def make (self):
		"""
		Process the Literate Haskell source into the LaTeX source.
		"""
		if not self.run_needed():
			return 0
		self.env.msg(0, _("pretty-printing %s.lhs...") % self.env.src_pbase)
		out = open(self.env.src_pbase + ".tex", 'w')
		def w (line, file=out):
		  file.write(line)
		  file.flush()
		if self.env.execute(["lhs2TeX", self.style, self.env.src_pbase + ".lhs"], out=w):
			out.close()
			self.env.msg(0, _("processing failed"))
			return 1
		out.close()
		return 0

	def command (self, cmd, arg):
		if cmd == "style":
			self.style = "-" + arg

	def run_needed (self):
		"""
		Check if processing is necessary.
		"""
		pbase = self.env.src_pbase
		if not exists(pbase + ".tex"):
			self.env.msg(2, _("the LaTeX source does not exist"))
			return 1
		if getmtime(pbase + ".tex") < getmtime(pbase + ".lhs"):
			self.env.msg(2, _("the Haskell source was modified"))
			return 1
		self.env.msg(2, _("the LaTeX source is up to date"))
		return 0

	def clean (self):
		"""
		Remove the LaTeX source produced by lhs2TeX.
		"""
		if self.clean_tex:
			self.env.remove_suffixes([".tex"])

	def convert (self, source, target, env):
		"""
		Return a dependency node for the given target and the given source
		file names.
		"""
		return Dep(source, target, env)
