# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2006
"""
Multibib support for Rubber

This package allows several bibliographies in one document. Each occurence of
the \\newcites macro creates a new bibliography with its associated commands,
using a new aux file. This modules behaves like the default BibTeX module for
each of those files.

The directives are the same as those of the BibTeX module. They all accept an
optional argument first, enclosed in parentheses as in "multibib.path
(foo,bar) here/", to specify which bibliography they apply to. Without this
argument, they apply to all bibliographies.
"""

import os, os.path, re

from rubber import _, msg
from rubber.latex_modules.bibtex import Bibliography

re_optarg = re.compile(r'\((?P<list>[^()]*)\) *')

def setup (document, context):
	global doc, bibs, defaults, commands
	doc = document
	bibs = {}
	defaults = []
	commands = {}
	doc.hook_macro('newcites', 'a', hook_newcites)

def command (cmd, args):
	names = None

	# Check if there is the optional argument.

	if len(args) > 0:
		match = re_optarg.match(args[0])
		if match:
			names = match.group('list').split(',')
			args = args[1:]

	# If not, this command will also be executed for newly created indices
	# later on.

	if names is None:
		defaults.append([cmd, args])
		names = bibs.keys()

	# Then run the command for each index it concerns.

	for name in names:
		if name in bibs:
			bibs[name].command(cmd, args)
		elif name in commands:
			commands[name].append([cmd, args])
		else:
			commands[name] = [[cmd, args]]

def hook_newcites (loc, name):
	bib = bibs[name] = Bibliography(doc, name)
	doc.hook_macro('bibliography' + name, 'a',
			bib.hook_bibliography)
	doc.hook_macro('bibliographystyle' + name, 'a',
			bib.hook_bibligraphystyle)
	for cmd in defaults:
		bib.command(*cmd)
	if name in commands:
		for cmd in commands[name]:
			bib.command(*cmd)
	msg.log(_("bibliography %s registered") % name, pkg='multibib')

def pre_compile ():
	for bib in bibs.values():
		if not bib.pre_compile():
			return False
	return True

def post_compile ():
	for bib in bibs.values():
		if not bib.post_compile():
			return False
	return True

def clean ():
	for bib in bibs.keys():
		for suffix in '.aux', '.bbl', '.blg':
			file = bib + suffix
			if os.path.exists(file):
				msg.log(_("removing %s") % file, pkg='multibib')
				os.unlink(file)
