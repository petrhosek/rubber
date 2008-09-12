# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Dependency analysis and environment parsing for package 'listings' in Rubber.
"""

def setup (document, context):
	global doc
	doc = document
	doc.hook_macro('lstinputlisting', 'oa', hook_input)
	doc.hook_macro('lstnewenvironment', 'a', hook_newenvironment)
	doc.hook_begin('lstlisting',
		lambda loc: doc.h_begin_verbatim(loc, env='lstlisting'))

def hook_input (loc, opt, file):
	if file.find('\\') < 0 and file.find('#') < 0:
		doc.add_source(file)

def hook_newenvironment (loc, name):
	doc.hook_begin(name,
		lambda loc: doc.h_begin_verbatim(loc, env=name))
