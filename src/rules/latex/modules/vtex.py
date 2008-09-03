# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
VTeX support for Rubber.

This module specifies that the VTeX/Free compiler should be used. This
includes using "vlatex" of "vlatexp" instead of "latex" and knowing that this
produces a PDF or PostScript file directly. The PDF version is used by
default, switching to PS is possible by using the module option "ps".
"""

import rubber

def setup (doc, context):
	doc.vars['engine'] = 'VTeX'
	if context['opt'] == 'ps':
		if doc.env.final != doc and doc.products[0][-4:] != '.ps':
			msg.error(_("there is already a post-processor registered"))
			sys.exit(2)
		doc.vars['program'] = 'vlatexp'
		doc.reset_products([doc.target + '.ps'])
	else:
		if doc.env.final != doc and doc.products[0][-4:] != '.pdf':
			msg.error(_("there is already a post-processor registered"))
			sys.exit(2)
		doc.vars['program'] = 'vlatex'
		doc.reset_products([doc.target + '.pdf'])
	doc.cmdline = ['-n1', '@latex', '%s']
