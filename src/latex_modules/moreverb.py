# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Dependency analysis and environment parsing for package 'moreverb' in Rubber.
"""

def setup (document, context):
	global doc
	doc = document
	doc.hook_macro('verbatimtabinput', 'oa', hook_verbatimtabinput)
	doc.hook_macro('listinginput', 'oaa', hook_listinginput)
	for env in [
		'verbatimtab', 'verbatimwrite', 'boxedverbatim', 'comment',
		'listing', 'listing*', 'listingcont', 'listingcont*']:
		doc.hook_begin(env, lambda loc: doc.h_begin_verbatim(loc, env=env))

def hook_verbatimtabinput (loc, tabwidth, file):
	if file.find('\\') < 0 and file.find('#') < 0:
		doc.add_source(file)

def hook_listinginput (loc, interval, start, file):
	if file.find('\\') < 0 and file.find('#') < 0:
		doc.add_source(file)
