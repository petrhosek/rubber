# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2004
"""
BibTeX support for Rubber

This module is a special one: it is triggered by the macros \\bibliography and
\\bibliographystyle and not as a package, so the main system knows about it.
The module provides the following commands:

  path <dir> = adds <dir> to the search path for databases
  stylepath <dir> = adds <dir> to the search path for styles
"""

from bisect import bisect_left
import os, sys
from os.path import *
import re, string

import rubber
from rubber import _
from rubber.util import *

re_citation = re.compile("\\citation{(?P<cite>.*)}")
re_undef = re.compile("LaTeX Warning: Citation `(?P<cite>.*)' .*undefined.*")

# The regular expression that identifies errors in BibTeX log files is heavily
# heuristic. The remark is that all error messages end with a text of the form
# "---line xxx of file yyy" or "---while reading file zzz". The actual error
# is either the text before the dashes or the text on the previous line.

re_error = re.compile(
	"---(line (?P<line>[0-9]+) of|while reading) file (?P<file>.*)")

class Module (rubber.Module):
	"""
	This class is the module that handles BibTeX in Rubber. It provides the
	funcionality required when compiling documents as well as material to
	parse blg files for diagnostics.
	"""
	def __init__ (self, env, dict, base=None):
		"""
		Initialize the state of the module and register appropriate functions
		in the main process. The extra arugment 'base' can be used to specify
		the base name of the aux file, it defaults to the document name.
		"""
		self.env = env
		self.msg = env.msg

		if base is None:
			self.base = env.src_base
		else:
			self.base = base

		self.bib_path = [""]
		if env.src_path != "" and env.src_path != ".":
			self.bib_path.append(env.src_path)
		self.bst_path = [""]

		self.undef_cites = None
		self.def_cites = None
		self.style = None
		self.set_style("plain")
		self.db = []
		self.run_needed = 0

	#
	# The following method are used to specify the various datafiles that
	# BibTeX uses.
	#

	def command (self, cmd, arg):
		if cmd == "path":
			self.bib_path.append(expanduser(arg))
		elif cmd == "stylepath":
			self.bst_path.append(expanduser(arg))

	def add_db (self, name):
		"""
		Register a bibliography database file.
		"""
		for dir in self.bib_path:
			bib = join(dir, name + ".bib")
			if exists(bib):
				self.db.append(bib)
				self.env.depends[bib] = DependLeaf([bib], self.msg)
				return

	def set_style (self, style):
		"""
		Define the bibliography style used. This method is called when
		\\bibliographystyle is found. If the style file is found in the
		current directory, it is considered a dependency.
		"""
		if self.style:
			old_bst = self.style + ".bst"
			if exists(old_bst) and self.env.depends.has_key(old_bst):
				del self.env.depends[old_bst]

		self.style = style
		for dir in self.bst_path:
			new_bst = join(dir, style + ".bst")
			if exists(new_bst):
				self.bst_file = new_bst
				self.env.depends[new_bst] = DependLeaf([new_bst], self.msg)
				return
		self.bst_file = None

	#
	# The following methods are responsible of detecting when running BibTeX
	# is needed and actually running it.
	#

	def pre_compile (self):
		"""
		Run BibTeX if needed before the first compilation. This function also
		checks if BibTeX has been run by someone else, and in this case it
		tells the system that it should recompile the document.
		"""
		self.run_needed = self.first_run_needed()
		if self.env.must_compile:
			# If a LaTeX compilation is going to happen, it is not necessary
			# to bother with BibTeX yet.
			return 0
		if self.run_needed:
			return self.run()

		bbl = self.base + ".bbl"
		if exists(bbl):
			if getmtime(bbl) > getmtime(self.env.src_base + ".log"):
				self.env.must_compile = 1
		return 0

	def first_run_needed (self):
		"""
		The condition is only on the database files' modification dates, but
		it would be more clever to check if the results have changed.
		BibTeXing is also needed in the very particular case when the style
		has changed since last compilation.
		"""
		if not exists(self.base + ".aux"):
			return 0
		if not exists(self.base + ".blg"):
			return 1
		dtime = getmtime(self.base + ".blg")
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

	def list_cites (self):
		"""
		Return the list of all defined citations (from the aux file, which is
		supposed to exist).
		"""
		list = []
		aux = open(self.base + ".aux")
		for line in aux.readlines():
			match = re_citation.match(line)
			if match:
				cite = match.group("cite")
				pos = bisect_left(list, cite)
				if pos == len(list):
					list.append(cite)
				elif list[pos] != cite:
					list.insert(pos, cite)
		aux.close()
		return list

	def list_undefs (self):
		"""
		Return the list of all undefined citations.
		"""
		list = []
		for line in self.env.log.lines:
			match = re_undef.match(line)
			if match:
				cite = match.group("cite")
				pos = bisect_left(list, cite)
				if pos == len(list):
					list.append(cite)
				elif list[pos] != cite:
					list.insert(pos, cite)
		return list

	def post_compile (self):
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
		This method actually runs BibTeX with the appropriate environment
		variables set.
		"""
		self.msg(0, _("running BibTeX on %s...") % self.base)
		env = {}
		if len(self.bib_path) != 1:
			env["BIBINPUTS"] = string.join(self.bib_path +
				[os.getenv("BIBINPUTS", "")], ":")
		if len(self.bst_path) != 1:
			env["BSTINPUTS"] = string.join(self.bst_path +
				[os.getenv("BSTINPUTS", "")], ":")
		if self.env.execute(["bibtex", self.base], env):
			self.msg(-1, _("There were errors making the bibliography."))
			self.show_errors()
			return 1
		self.run_needed = 0
		self.env.must_compile = 1
		return 0

	def bibtex_needed (self):
		"""
		Return true if BibTeX must be run.
		"""
		if self.run_needed:
			return 1
		self.msg(2, _("checking if BibTeX must be run..."))

		# If there was a list of undefined citations, we check if it has
		# changed. If it has and it is not empty, we have to rerun.

		if self.undef_cites:
			new = self.list_undefs()
			if new == []:
				self.msg(2, _("no more undefined citations"))
				self.undef_cites = new
			elif self.undef_cites != new:
				self.msg(2, _("the list of undefined citations changed"))
				self.undef_cites = new
				return 1
			else:
				self.msg(2, _("the undefined citations are the same"))
				return 0
		else:
			self.undef_cites = self.list_undefs()

		# At this point we don't know if undefined citations changed. If
		# BibTeX has not been run before (i.e. there is no log file) we know
		# that it has to be run now.

		blg = self.base + ".blg"
		if not exists(blg):
			self.msg(2, _("no BibTeX log file"))
			return 1

		# Here, BibTeX has been run before but we don't know if undefined
		# citations changed.

		if self.undef_cites == []:
			self.msg(2, _("no undefined citations"))
			return 0

		log = self.env.src_base + ".log"
		if getmtime(blg) < getmtime(log):
			self.msg(2, _("BibTeX's log is older than the main log"))
			return 1

		return 0

	def clean (self):
		self.env.remove_suffixes([".bbl", ".blg"])

	#
	# The following method extract information from BibTeX log files.
	#

	def style_changed (self):
		"""
		Read the log file if it exists and check if the style used is the one
		specified in the source. This supposes that the style is mentioned on
		a line with the form 'The style file: foo.bst'.
		"""
		blg = self.base + ".blg"
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

	def show_errors (self):
		"""
		Read the log file, identify error messages and report them.
		"""
		blg = self.base + ".blg"
		if not exists(blg):
			return 1
		log = open(blg)
		last_line = ""
		line = log.readline()
		while line != "":
			m = re_error.search(line)
			if m:
				# TODO: it would be possible to report the offending code.
				if m.start() == 0:
					text = string.strip(last_line)
				else:
					text = string.strip(line[:m.start()])
				line = m.group("line")
				if line: line = int(line)
				self.env.msg.error(m.group("file"), line, text, None)
			last_line = line
			line = log.readline()
		log.close()
		return 0
