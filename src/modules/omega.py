# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004
"""
Omega support for Rubber.
"""

import sys
import rubber
from rubber import _

class Module (rubber.Module):
	def __init__ (self, env, dict):
		env.conf.latex = "lambda"
		env.conf.tex = "Omega"
