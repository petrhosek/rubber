# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
"""
Natbib support for Rubber

This package handles the behaviour specific to natbib, i.e. the fact that an
extra compilation may be needed when using this package.
"""

import re

import rubber

re_rerun = re.compile("\(natbib\).*Rerun ")

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env

	def post_compile (self):
		for line in self.env.log.lines:
			if re_rerun.match(line):
				self.env.must_compile = 1
				return 0
		return 0
