# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2005
"""
PostScript to PDF conversion using GhostScript.
"""

import sys

import rubber
from rubber import _, msg
from rubber.util import *

class Module (DependShell, rubber.Module):
	def __init__ (self, env, dict):
		if env.final.prods[0][-3:] != ".ps":
			msg.error(_("I can't use ps2pdf when not producing a PS"))
			sys.exit(2)
		ps = env.final.prods[0]
		pdf = ps[:-2] + "pdf"
		cmd = ["ps2pdf"]
		for opt in env.conf.paper:
			cmd.append("-sPAPERSIZE=" + opt)
		cmd.extend([ps, pdf])
		DependShell.__init__(self, [pdf], { ps: env.final }, cmd, env)
		env.final = self
