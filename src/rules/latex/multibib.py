# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004--2005
"""
Multibib support for Rubber

This package allows several bibliographies in one document. Each occurence of
the \\newcites macro creates a new bibliography with its associated commands,
using a new aux file. This modules behaves like the default BibTeX module for
each of those files.
"""

import os
from os.path import *
import string

import rubber, rubber.rules.latex, rubber.rules.latex.bibtex
from rubber import _, msg

class Biblio (rubber.rules.latex.bibtex.Module):
	def __init__ (self, doc, name):
		rubber.rules.latex.bibtex.Module.__init__(self, doc, {}, name)
		doc.add_hook("bibliographystyle" + name, self.bibstyle)
		doc.add_hook("bibliography" + name, self.biblio)

	def bibstyle (self, dict):
		self.set_style(dict["arg"])

	def biblio (self, dict):
		for bib in string.split(dict["arg"], ","):
			self.add_db(bib)

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		"""
		Initialize the module with no extra bibliography.
		"""
		self.doc = doc
		self.bibs = {}
		doc.add_hook("newcites", self.newcites)

	def newcites (self, dict):
		"""
		Register a new bibliography.
		"""
		bib = dict["arg"]
		self.bibs[bib] = Biblio(self.doc, bib)
		msg.log(_("bibliography %s registered") % bib)

	def pre_compile (self):
		for bib in self.bibs.values():
			if bib.pre_compile():
				return 1

	def post_compile (self):
		for bib in self.bibs.values():
			if bib.post_compile():
				return 1

	def clean (self):
		for bib in self.bibs.keys():
			for suffix in ".aux", ".bbl", ".blg":
				file = bib + suffix
				if exists(file):
					msg.log(_("removing %s") % file)
					os.unlink(file)
