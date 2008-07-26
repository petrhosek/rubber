# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2006
"""
PostScript to PDF conversion using GhostScript.
"""

import sys

import rubber
from rubber import _
from rubber import *

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		env = doc.env
		if env.final.prods[0][-3:] != ".ps":
			msg.error(_("I can't use ps2pdf when not producing a PS"))
			sys.exit(2)
		ps = env.final.prods[0]
		pdf = ps[:-2] + "pdf"
		cmd = ["ps2pdf"]
		for opt in doc.vars["paper"].split():
			cmd.append("-sPAPERSIZE=" + opt)
		cmd.extend([ps, pdf])
		dep = DependShell(doc.env, cmd, prods=[pdf], sources={ ps: env.final })
		env.final = dep
