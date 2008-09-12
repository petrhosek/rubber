# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
Dependency analysis for the xr package.

The xr package allows one to put references in one document to other
(external) LaTeX documents. It works by reading the external document's .aux
file, so this support package registers these files as dependencies.
"""

from rubber import _, msg

def setup (document, context):
	global doc
	doc = document
	doc.hook_macro('externaldocument', 'oa', hook_externaldocument)

def hook_externaldocument (loc, opt, name):
	aux = doc.env.find_file(name + '.aux')
	if aux:
		doc.add_source(aux)
		msg.log( _(
			"dependency %s added for external references") % aux, pkg='xr')
	else:
		msg.log(_(
			"file %s is required by xr package but not found") % aux, pkg='xr')
