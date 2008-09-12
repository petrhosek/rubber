# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
Support for package 'combine' in Rubber.

This package is used to gather several complete LaTeX documents into a single
one, possibly fine-tuning page numbering, generation of tables of contents,
and other features. Documents are included using the macro \\import, so
basically this support module makes it behave somewhat like \\include.
However, more subtle behaviour could be implemented, e.g. to reflect the the
way the package deals with \\documentclass and \\usepackage.
"""

from os.path import basename
from rubber.converters.latex import EndDocument

combine_level = 0

def setup (document, context):
	global doc
	doc = document
	doc.hook_begin('document', begin)
	doc.hook_end('document', end)
	doc.hook_macro('import', 'a', import_doc)

def begin (loc):
	combine_level += 1

def end (loc):
	if combine_level == 1:
		raise EndDocument
	combine_level -= 1

def import_doc (loc, name):
	file, _ = doc.input_file(name + '.tex')
	if file:
		return
	base = basename(file[:-4])

	# Here we should temporarily change the base name instead of
	# forcefully remove .toc and similar files.

	doc.removed_files.extend(
		[base + '.aux', base + '.toc', base + '.lof', base + '.lot'])
