# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2004
"""
Support for the beamer package.
"""

import rubber

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		env.watch_file(env.src_base + ".head")
		env.watch_file(env.src_base + ".nav")
		env.watch_file(env.src_base + ".snm")
		env.command("module", "hyperref")

	def clean (self):
		self.env.remove_suffixes([".head", ".nav", ".snm"])
