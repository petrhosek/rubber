# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
"""
Support for the beamer package.
"""

import rubber

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		env.watch_file(env.src_base + ".head")

	def clean (self):
		self.env.remove_suffixes([".head"])
