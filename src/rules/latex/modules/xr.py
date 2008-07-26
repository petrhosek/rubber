# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
Dependency analysis for the xr package.

The xr package allows one to put references in one document to other
(external) LaTeX documents. It works by reading the external document's .aux
file, so this support package registers these files as dependencies.
"""

import rubber
from rubber import _
from rubber import *

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		self.env = doc.env
		doc.add_hook("externaldocument", self.externaldocument)

	def externaldocument (self, dict):
		aux = self.env.find_file(dict["arg"] + ".aux")
		if aux:
			self.doc.sources[aux] = DependLeaf(self.env, aux)
			msg.log( _(
				"dependency %s added for external references") % aux, pkg="xr")
		else:
			msg.log(_(
				"file %s is required by xr package but not found") % aux, pkg="xr")
