# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
Support for the minitoc package.

This package allows for the insertion of partial tables of contents at the
level of chapters, parts and sections. This nice feature has the drawback of
producing a lot of auxiliary files, and this module handles the cleaning of
these.

TODO: handle the shortext option
"""

import os, os.path
import re

import rubber
from rubber import _, msg

re_tocext = re.compile("[mps](tc|l[ft])[0-9]+")

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env

	def clean (self):
		self.env.remove_suffixes([".bmt"])
		base = self.env.src_base + "."
		ln = len(base)
		for file in os.listdir("."):
			if file[:ln] == base:
				ext = file[ln:]
				m = re_tocext.match(ext)
				if m and ext[m.end():] == "":
					msg.log(_("removing %s") % file)
					os.unlink(file)
