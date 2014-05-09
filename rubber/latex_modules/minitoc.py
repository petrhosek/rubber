# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
Support for the minitoc package.

This package allows for the insertion of partial tables of contents at the
level of chapters, parts and sections. This nice feature has the drawback of
producing a lot of auxiliary files, and this module handles the cleaning of
these.

TODO: handle the shortext option
"""

import os
import re

from rubber import _, msg

re_tocext = re.compile("[mps](tc|l[ft])[0-9]+")

def setup (document, context):
	global doc
	doc = document

def clean ():
	doc.remove_suffixes(['.bmt'])
	base = doc.target + '.'
	ln = len(base)
	for file in os.listdir('.'):
		if file[:ln] == base:
			ext = file[ln:]
			m = re_tocext.match(ext)
			if m and ext[m.end():] == "":
				msg.log(_("removing %s") % file, pkg='minitoc')
				os.unlink(file)
