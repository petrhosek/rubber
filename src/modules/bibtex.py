# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
BibTeX support for Rubber
"""

from bisect import bisect_left
import os
from os.path import *
import re
import string
import sys

def _ (txt):
	return txt

class Module:
	"""
	This class is the module that handles BibTeX in Rubber.
	"""
	def __init__ (self, env, dict):
		"""
		Initialize the state of the module and register appropriate functions
		in the main process.
		"""
		self.env = env
		self.msg = env.message
		self.log = env.logcheck

		self.undef_cites = None
		self.set_style("plain")
		self.db = []
		self.run_needed = 0

		env.process.depends.append(env.process.src_pbase + ".bbl")
		env.process.ext_building.append(self.first_bib)
		env.process.compile_process.append(self.check_bib)
		env.process.cleaning_process.append(self.clean)

		self.re_cite = re.compile(
			"LaTeX Warning: Citation `(?P<cite>.*)' .*undefined.*")

	def add_db (self, name):
		"""
		Register a bibliography database file.
		"""
		if exists(name + ".bib"):
			self.db.append(name + ".bib")

	def set_style (self, style):
		"""
		Define the bibliography style used. This method is called when
		\\bibliographystyle is found. If the style file is found in the
		current directory, it is considered a dependency.
		"""
		self.style = style
		if exists(style + ".bst"):
			self.bst_file = style + ".bst"
		else:
			self.bst_file = None

	def first_bib (self):
		"""
		Run BibTeX if needed before the first compilation.
		"""
		self.run_needed = self.first_run_needed()
		if self.env.process.must_compile:
			return 0
		if self.run_needed:
			return self.run()

	def first_run_needed (self):
		"""
		The condition is only on the database files' modification dates, but
		it would be more clever to check if the results have changed.
		BibTeXing is also needed in the very particular case when the style
		has changed since last compilation.
		"""
		if not exists(self.env.process.src_pbase + ".aux"):
			return 0
		if not exists(self.env.process.src_pbase + ".blg"):
			return 1
		dtime = getmtime(self.env.process.src_pbase + ".blg")
		for db in self.db:
			if getmtime(db) > dtime:
				self.msg(2, _("bibliography database %s was modified") % db)
				return 1
		if self.style_changed():
			return 1
		if self.bst_file and getmtime(self.bst_file) > dtime:
			self.msg(2, _("the bibliography style file was modified"))
			return 1
		return 0

	def style_changed (self):
		"""
		Read the log file if it exists and check if the style used is the one
		specified in the source. This supposes that the style is mentioned on
		a line with the form 'The style file: foo.bst'.
		"""
		blg = self.env.process.src_pbase + ".blg"
		if not exists(blg):
			return 0
		log = open(blg)
		line = log.readline()
		while line != "":
			if line[:16] == "The style file: ":
				if line.rstrip()[16:-4] != self.style:
					self.msg(2, _("the bibliography style was changed"))
					log.close()
					return 1
			line = log.readline()
		log.close()
		return 0

	def list_cites (self):
		"""
		Return the list of all undefined citations.
		"""
		list = []
		for line in self.log.lines:
			match = self.re_cite.match(line)
			if match:
				cite = match.group("cite")
				pos = bisect_left(list, cite)
				if pos == len(list):
					list.append(cite)
				elif list[pos] != cite:
					list.insert(pos, cite)
		return list


	def check_bib (self):
		"""
		This method runs BibTeX if needed to solve undefined citations. If it
		was run, then force a new LaTeX compilation.
		"""
		if not self.bibtex_needed():
			self.msg(2, _("no BibTeXing needed"))
			return 0
		return self.run()

	def run (self):
		"""
		This method actually runs BibTeX.
		"""
		self.msg(0, _("running BibTeX..."))
		self.env.process.execute(
			["bibtex", "-terse", self.env.process.src_pbase])
		self.run_needed = 0
		self.env.process.must_compile = 1
		return 0

	def bibtex_needed (self):
		"""
		Return true if BibTeX must be run.
		"""
		if self.run_needed:
			return 1
		self.msg(2, _("checking if BibTeX must be run..."))

		if self.undef_cites:
			new = self.list_cites()
			if new == []:
				self.msg(2, _("no more undefined citations"))
				self.undef_cites = new
				return 0
			if self.undef_cites != new:
				self.msg(2, _("the list of undefined citations changed"))
				self.undef_cites = new
				return 1
			self.msg(2, _("the undefined citations are the same"))
			return 0
		
		self.undef_cites = self.list_cites()

		if self.undef_cites == []:
			self.msg(2, _("no undefined citations"))
			return 0

		blg = self.env.process.src_pbase + ".blg"
		if not exists(blg):
			self.msg(2, _("no BibTeX log file"))
			return 1

		log = self.env.process.src_pbase + ".log"
		if getmtime(blg) < getmtime(log):
			self.msg(2, _("BibTeX's log is older than the main log"))
			return 1

		return 0

	def clean (self):
		self.env.process.remove_suffixes([".bbl", ".blg"])
