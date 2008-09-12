# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2008
"""
Support for nomenclatures with package 'nomencl'.

This module simply wraps the functionality of the 'index' module with default
values for the 'nomencl' package.
"""

from rubber.latex_modules.index import Index

def setup (document, context):
	global index
	index = Index(document, 'nlo', 'nls', 'ilg')
	index.do_style('nomencl.ist')

def post_compile ():
	return index.post_compile()

def command (command, args):
	getattr(index, 'do_' + command)(*args)
