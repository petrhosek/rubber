# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
BibTeX support for Rubber
"""

from bisect import bisect_left
import os
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

		if dict["arg"]:
			for db in dict["arg"].split(","):
				if os.path.exists(db + ".bib"):
					env.process.depends.append(db + ".bib")
		env.process.compile_process.append(self.check_bib)
		env.process.cleaning_process.append(self.clean)

		self.re_cite = re.compile("LaTeX Warning: Citation `(?P<cite>.*)' .*undefined.*")

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
		self.msg(0, _("running BibTeX..."))
		self.env.process.execute(["bibtex", self.env.process.src_pbase])
		self.env.process.must_compile = 1

	def bibtex_needed (self):
		"""
		Return true if BibTeX must be run.
		"""
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
		if not os.path.exists(blg):
			self.msg(2, _("no BibTeX log file"))
			return 1

		log = self.env.process.src_pbase + ".log"
		if os.path.getmtime(blg) < os.path.getmtime(log):
			self.msg(2, _("BibTeX's log is older than the main log"))
			return 1

		return 0

	def clean (self):
		self.env.process.remove_suffixes([".bbl", ".blg"])
