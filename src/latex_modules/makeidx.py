# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006

from rubber.latex_modules.index import Index

def setup (document, context):
	global index
	index = Index(document, 'idx', 'ind', 'ilg')
def post_compile ():
	return index.post_compile()
def clean ():
	index.clean()
def command (command, args):
	getattr(index, 'do_' + command)(*args)
