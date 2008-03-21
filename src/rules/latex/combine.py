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
import rubber

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		self.doc = doc
		del doc.hooks["end{document}"]
		doc.add_hook("import", self.import_doc)

	def import_doc (self, dict):
		if not dict["arg"]:
			return 0
		file, _ = self.doc.input_file(dict["arg"] + ".tex")
		if not file:
			return 0
		base = basename(file[:-4])

		# Here we should temporarily change the base name instead of
		# forcefully remove .toc and similar files.

		self.doc.removed_files.extend(
			[base + ".aux", base + ".toc", base + ".lof", base + ".lot"])
