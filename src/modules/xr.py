# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
Dependency analysis for the xr package.

The xr package allows one to put references in one document to other
(external) LaTeX documents. It works by reading the external document's .aux
file, so this support package registers these files as dependencies.
"""

from rubber.util import DependLeaf

def _ (txt): return txt

class Module:
	def __init__ (self, env, dict):
		self.env = env
		env.add_hook("externaldocument", self.externaldocument)

	def externaldocument (self, dict):
		aux = self.env.conf.find_input(dict["arg"] + ".aux")
		if aux:
			self.env.depends[aux] = DependLeaf([aux])
			self.env.msg(2, _(
				"dependency %s added for external references") % aux)
		else:
			self.env.msg(3, _(
				"file %s is required by xr package but not found") % aux)
