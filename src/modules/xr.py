# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
Dependency analysis for the xr package.

The xr package allows one to put references in one document to other
(external) LaTeX documents. It works by reading the external document's .aux
file, so this support package registers these files as dependencies.
"""

import rubber
from rubber import _, msg
from rubber.util import DependLeaf

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		env.add_hook("externaldocument", self.externaldocument)

	def externaldocument (self, dict):
		aux = self.env.conf.find_input(dict["arg"] + ".aux")
		if aux:
			self.env.sources[aux] = DependLeaf([aux])
			msg.log( _(
				"dependency %s added for external references") % aux)
		else:
			msg.log(_(
				"file %s is required by xr package but not found") % aux)
