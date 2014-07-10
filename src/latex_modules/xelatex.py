# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
XeLaTeX support for Rubber.

When this module is loaded with the otion 'xdv', the document is compiled to
XDV using XeLaTeX.
"""

from rubber import _, msg

def setup(doc, context):
    doc.vars['program'] = 'xelatex'
    doc.vars['engine'] = 'XeLaTeX'
    if 'opt' in context and context['opt'] == 'xdv':
		mode_xdv()
	else:
		mode_pdf()

def mode_pdf ():
	global mode
	if mode == 'pdf':
		return
	if doc.env.final != doc and doc.products[0][-4:] != '.pdf':
		msg.error(_("there is already a post-processor registered"))
		return
	doc.reset_products([doc.target + '.pdf'])
	doc.cmdline = [
		opt for opt in doc.cmdline if opt != '-no-pdf']
	mode = 'pdf'

def mode_xdv ():
	global mode
	if mode == 'xdv':
		return
	if doc.env.final != doc and doc.products[0][-4:] != '.xdv':
		msg.error(_("there is already a post-processor registered"))
		return
	doc.reset_products([doc.target + '.xdv'])
	doc.cmdline.insert(0, '-no-pdf')
	mode = 'xdv'
