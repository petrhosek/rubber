# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2005
"""
This module is used to produce a final self-contained version of the source of
a document, as may be required when preparing a manuscript for an editor. It
mainly replaces \\input and \\include macros by the contents of the files they
include, and replaces bibliography macros by the contents of the bbl file.
The expansion also works in a naive way with local packages and classes,
though the result is likely to fail if a local package uses options.

This package accepts the following options (separated by commas):
  - class : expand \\documentclass even when the class is local
  - nopkg : don't expand \\usepackage even for local packages
  - nobib : don't include the bibliography explicitly
"""

import sys
from os.path import *
import string, re

import rubber
from rubber import _, msg
from rubber.util import *

class Module (Depend, rubber.rules.latex.Module):
	def __init__ (self, doc, dict):

		# register as the post-processor

		if doc.env.final != doc:
			msg.error(_("there is already a post-processor registered"))
			sys.exit(2)

		self.doc = doc
		self.out = doc.src_base + "-final.tex"

		# FIXME: we make foo-final.tex depend on foo.dvi so that all auxiliary
		#   files are built when expanding, this could be optimised...

		Depend.__init__(self, doc.env,
				prods=[self.out], sources={ doc.prods[0]: doc })
		doc.env.final = self

		# initialise the expansion table
		
		self.hooks = {
			"input" : doc.h_input,
			"include" : doc.h_include,
			"usepackage" : self.x_usepackage,
			"RequirePackage" : self.x_usepackage,
			"bibliography" : self.x_remove,
			"bibliographystyle" : self.x_bibliographystyle,
			"end{document}" : doc.h_end_document
		}

		self.pkg_hooks = {
			"NeedsTeXFormat" : self.x_remove_b,
			"ProvidesPackage" : self.x_remove_b,
			"DeclareOption" : self.x_option,
			"ProcessOptions" : self.x_process
		}

		if dict.has_key("opt") and dict["opt"]:
			for opt in string.split(dict["opt"], ","):
				if opt == "class":
					self.hooks["documentclass"] = self.x_documentclass
				elif opt == "nopkg":
					del self.hooks["usepackage"]
					del self.hooks["RequirePackage"]
				elif opt == "nobib":
					del self.hooks["bibliography"]
					del self.hooks["bibliographystyle"]

		self.opt_lists = []   # stack of package option lists
		self.opt_texts = []   # stack of used options

	def run (self):
		msg.progress(_("writing %s") % (self.out))
		self.out_stream = open(self.out, "w")

		# This is sort of a hack: we replace the 'seq' and 'hook' fields in
		# the environment with our own, in order to reuse the parsing routine.

		doc = self.doc
		saved_seq = doc.seq #; doc.seq = self.seq
		saved_hooks = doc.hooks ; doc.hooks = self.hooks
		doc.update_seq()
		try:
			try:
				self.expand_path(self.doc.source())
			except rubber.EndDocument:
				self.out_stream.write("\\end{document}\n")
		finally:
			doc.hooks = saved_hooks
			doc.seq = saved_seq

		self.out_stream.close()
		self.doc.env.something_done = 1

	def expand_path (self, path):
		# self.out_stream.write("%%--- beginning of file %s\n" % path)
		file = open(path)
		try:
			self.doc.do_process(file, path, dump=self.out_stream)
		finally:
			file.close()
		# self.out_stream.write("%%--- end of file %s\n" % path)

	#
	#  The simple expansion hooks
	#

	def x_remove (self, dict):
		pass

	def x_documentclass (self, dict):
		if not dict["arg"]: return
		file = self.env.find_file(dict["arg"] + ".cls")
		if file:
			self.out_stream.write("\\makeatletter\n")
			self.expand_path(file)
			self.out_stream.write("\\makeatother\n")
		else:
			self.out_stream.write(dict["match"])

	def x_bibliographystyle (self, dict):
		if not dict["arg"]: return
		bbl = self.doc.src_base + ".bbl"
		if exists(bbl):
			self.expand_path(bbl)

	#
	#  Package expansion
	#

	def x_usepackage (self, dict):
		if not dict["arg"]: return
		remaining = []

		# Dump the contents of local packages.

		for name in string.split(dict["arg"], ","):
			file = self.env.find_file(name + ".sty")
			if file and not exists(name + ".py"):

				# switch to package mode if needed

				if self.opt_lists == []:
					self.out_stream.write("\\makeatletter\n")
				if dict["opt"] is None:
					self.opt_lists.append([])
				else:
					self.opt_lists.append(string.split(dict["opt"], ","))
				self.opt_texts.append("")

				# register new macros

				for key, val in self.pkg_hooks.items():
					self.doc.hooks[key] = val
				self.doc.update_seq()

				# expand the package

				self.expand_path(file)

				# switch back to normal mode

				self.opt_lists.pop()
				self.opt_texts.pop()
				if self.opt_lists == []:
					self.out_stream.write("\\makeatother\n")
					for key in self.pkg_hooks.keys():
						del self.doc.hooks[key]
					self.doc.update_seq()

			else:
				remaining.append(name)

		# Rewrite a '\usepackage' for the remaining packages

		if remaining != []:
			self.out_stream.write("\\usepackage")
			if dict.has_key("opt") and dict["opt"]:
					self.out_stream.write("[%s]" % dict["opt"])
			self.out_stream.write("{%s}" % string.join(remaining, ","))

	def x_remove_b (self, dict):
		"""
		This is used to remove a macro and a possibly following argument in
		brackets, as in \\ProvidesPackage{foo}[2003/10/15].
		"""
		print "FIXME: x_remove_b"

	def x_option (self, dict):
		"""
		Parse an option definition.
		"""
		line = string.lstrip(dict["line"])
		if len(line) == 0 or line[0] != "{":
			print "FIXME: option %r"
			return
		arg, next = match_brace(line[1:])
		self.opt_texts[-1] = self.opt_texts[-1] + arg
		dict["line"] = next

	def x_process (self, dict):
		self.out_stream.write(self.opt_texts[-1])
