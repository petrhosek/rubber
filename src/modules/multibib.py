# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2004
"""
Multibib support for Rubber

This package allows several bibliographies in one document. Each occurence of
the \\newcites macro creates a new bibliography with its associated commands,
using a new aux file. This modules behaves like the default BibTeX module for
each of those files.
"""

import os
from os.path import *

import rubber, rubber.modules, rubber.modules.bibtex
from rubber import _

class Biblio (rubber.modules.bibtex.Module):
	def __init__ (self, env, name):
		rubber.modules.bibtex.Module.__init__(self, env, {}, name)

class Module (rubber.Module):
	def __init__ (self, env, dict):
		"""
		Initialize the module with no extra bibliography.
		"""
		self.env = env
		self.bibs = {}
		env.add_hook("newcites", self.newcites)

	def newcites (self, dict):
		"""
		Register a new bibliography.
		"""
		bib = dict["arg"]
		self.bibs[bib] = Biblio(self.env, bib)
		self.env.msg(1, _("bibliography %s registered") % bib)

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
					self.env.msg(1, _("removing %s") % file)
					os.unlink(file)
