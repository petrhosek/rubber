# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004
"""
e-TeX support for Rubber.
"""

import sys
import rubber
from rubber import _, msg

class Module (rubber.Module):
	def __init__ (self, env, dict):
		env.conf.latex = "elatex"
		env.conf.tex = "e-TeX"
