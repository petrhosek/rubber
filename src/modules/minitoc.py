# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
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

def _ (txt): return txt

re_tocext = re.compile("[mps](tc|l[ft])[0-9]+")

class Module:
	def __init__ (self, env, dict):
		self.env = env
		env.cleaning_process.append(self.clean)

	def clean (self):
		self.env.remove_suffixes([".bmt"])
		path = self.env.src_path
		base = self.env.src_base + "."
		ln = len(base)
		for file in os.listdir(path):
			if file[:ln] == base:
				ext = file[ln:]
				m = re_tocext.match(ext)
				if m and ext[m.end():] == "":
					file = os.path.join(path, file)
					self.env.msg(3, _("removing %s") % file)
					os.unlink(file)
