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

import os
from os.path import *
import re, string

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
			self.add_db(bib.strip())

re_optarg = re.compile("\((?P<list>[^()]*)\) *")

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		"""
		Initialize the module with no extra bibliography.
		"""
		self.doc = doc
		self.bibs = {}
		self.defaults = []
		self.commands = {}
		doc.add_hook("newcites", self.newcites)

	def command (self, cmd, args):
		bibs = self.bibs
		names = None
		if len(args) > 0:
			m = re_optarg.match(args[0])
			if m:
				names = m.group("list").split(",")
				args = args[1:]
		if names is None:
			self.defaults.append([cmd, args])
			names = bibs.keys()
		for name in names:
			if bibs.has_key(name):
				bibs[name].command(cmd, args)
			elif self.commands.has_key(name):
				self.commands[name].append([cmd, args])
			else:
				self.commands[name] = [[cmd, args]]

	def newcites (self, dict):
		"""
		Register a new bibliography.
		"""
		name = dict["arg"]
		bib = self.bibs[name] = Biblio(self.doc, name)
		for cmd in self.defaults:
			bib.command(*cmd)
		if self.commands.has_key(name):
			for cmd in self.commands[name]:
				bib.command(*cmd)
		msg.log(_("bibliography %s registered") % name, pkg="multibib")

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
					msg.log(_("removing %s") % file, pkg="multibib")
					os.unlink(file)
