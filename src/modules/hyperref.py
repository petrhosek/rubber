# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004
"""
Support for the hyperref package.
"""

import rubber

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		env.watch_file(env.src_base + ".out")

	def clean (self):
		self.env.remove_suffixes([".out"])
