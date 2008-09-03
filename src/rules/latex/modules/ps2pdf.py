# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2006
"""
PostScript to PDF conversion using GhostScript.
"""

import sys
from rubber.depend import Shell

def setup (doc, context):
	env = doc.env
	if env.final.products[0][-3:] != '.ps':
		msg.error(_("I can't use ps2pdf when not producing a PS"))
		sys.exit(2)
	ps = env.final.products[0]
	pdf = ps[:-2] + 'pdf'
	cmd = ['ps2pdf']
	for opt in doc.vars['paper'].split():
		cmd.append('-sPAPERSIZE=' + opt)
	cmd.extend([ps, pdf])
	dep = Shell(doc.env.depends, cmd, [pdf], [ps])
	env.final = dep
