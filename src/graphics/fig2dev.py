# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Conversion of XFig graphics into various formats.
"""

from rubber import _, msg
from rubber.util import *

import string

class Dep (Depend):
	def __init__ (self, target, source, env):
		leaf = DependLeaf([source])
		Depend.__init__(self, [target], {source: leaf})
		self.env = env
		self.source = source

		# Here we assume the target has an extension of a standard form, i.e.
		# its requested type can be deduced from the part of its name after
		# the last dot. We also assume that this extension is the name of the
		# appropriate language (it works fine in the cases where the module is
		# used, that is for eps, pdf and png).

		lang = target[string.rfind(target, ".")+1:]
		self.lang = string.upper(lang)
		
		self.cmd = ["fig2dev", "-L", lang, source, target]

	def run (self):
		msg.progress(_("converting %s to %s") % (self.source, self.lang))
		if self.env.execute(self.cmd):
			msg.error(_("converstion of %s to %s failed")
					% (self.source, self.lang))
			return 1
		return 0

def convert (source, target, env):
	if not prog_available("fig2dev"):
		return None
	return Dep(target, source, env)
