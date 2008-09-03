# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Dependency analysis and environment parsing for package 'verbatim' in Rubber.
"""

def setup (document, context):
	global doc
	doc = document
	doc.hook_macro('verbatiminput', 'a', hook_input)
	doc.hook_begin('comment',
		lambda loc: doc.h_begin_verbatim(loc, env='comment'))

def hook_input (loc, file):
	if file.find('\\') < 0 and file.find('#') < 0:
		doc.add_source(file)
