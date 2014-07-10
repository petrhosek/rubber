# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
LuaTeX support for Rubber.

When this module is loaded with the otion 'dvi', the document is compiled to
DVI using LuaTeX.
"""

from rubber import _, msg

def setup(doc, context):
    doc.vars['program'] = 'luatex'
    doc.vars['engine'] = 'LuaTeX'
    if 'opt' in context and context['opt'] == 'dvi':
		mode_dvi()
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
		opt for opt in doc.cmdline if opt != '-output-format dvi']
	mode = 'pdf'

def mode_dvi ():
	global mode
	if mode == 'dvi':
		return
	if doc.env.final != doc and doc.products[0][-4:] != '.dvi':
		msg.error(_("there is already a post-processor registered"))
		return
	doc.reset_products([doc.target + '.dvi'])
	doc.cmdline.insert(0, '-output-format dvi')
	mode = 'dvi'
