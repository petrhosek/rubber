# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2004
"""
Dependency analysis for package 'moreverb' in Rubber.
"""

from os.path import basename
import rubber
from rubber.util import *

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		env.add_hook("verbatimtabinput", self.input)
		env.add_hook("listinginput", self.listinginput)

	def input (self, dict):
		if not dict["arg"]:
			return 0
		file = dict["arg"]
		if file.find("\\") < 0 and file.find("#") < 0:
			self.env.sources[file] = DependLeaf([file],
					dict["pos"])

	def listinginput (self, dict):
		if not dict["arg"]:
			return 0
		file = get_next_arg(dict)
		if not file:
			return 0
		if file.find("\\") < 0 and file.find("#") < 0:
			self.env.sources[file] = DependLeaf([file],
					dict["pos"])
