# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004
"""
e-TeX support for Rubber.
"""

import sys
import rubber
from rubber import _, msg

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		doc.conf.latex = "elatex"
		doc.conf.tex = "e-TeX"
