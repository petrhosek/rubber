# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
"""
This module is used to produce a final self-contained version of the source of
a document, as may be required when preparing a manuscript for an editor. It
mainly replaces \\input and \\include macros by the contents of the files they
include, and replaces bibliography macros by the contents of the bbl file.
The expansion also works in a naive way with local packages and classes,
though the result is likely to fail if a local package uses options.

This package accepts the following options (separated by commas):
  - nopkg : don't expand \\usepackage even for local packages
  - nocls : don't expand \\documentclass even when the class is local
  - nobib : don't include the bibliography explicitly
"""

import sys
from os.path import *
import string, re

import rubber
from rubber import _

class Module (rubber.Module):
	def __init__ (self, env, dict):
		self.env = env
		self.msg = env.msg

		# register as the post-processor

		if env.output_processing:
			self.msg(0, _("there is already a post-processor registered"))
			sys.exit(2)
		env.output_processing = self.expand
		env.final_file = env.src_base + "-final.tex"

		# initialise the expansion table
		
		self.hooks = {
			"input" : env.h_input,
			"include" : env.h_include,
			"usepackage" : self.x_usepackage,
			"RequirePackage" : self.x_usepackage,
			"documentclass" : self.x_documentclass,
			"bibliography" : self.x_remove,
			"bibliographystyle" : self.x_bibliographystyle
		}

		if dict.has_key("opt") and dict["opt"]:
			for opt in string.split(dict["opt"], ","):
				if opt == "nopkg":
					del self.hooks["usepackage"]
					del self.hooks["RequirePackage"]
				elif opt == "nocls":
					del self.hooks["documentclass"]
				elif opt == "nobib":
					del self.hooks["bibliography"]
					del self.hooks["bibliographystyle"]

		self.seq = re.compile("\
\\\\(?P<name>%s)\*?\
 *(\\[(?P<opt>[^\\]]*)\\])?\
 *({(?P<arg>[^{}]*)}|(?=[^A-Za-z]))"
			% string.join(self.hooks.keys(), "|"))

	def clean (self):
		self.env.remove_suffixes(["-final.tex"])

	def expand (self):
		if not self.expand_needed():
			return 0
		self.msg(0, _("writing %s...") % (self.env.src_base + "-final.tex"))
		self.out_stream = open(self.env.src_base + "-final.tex", "w")
		self.expand_path(self.env.source())
		self.out_stream.close()
		self.env.something_done = 1

	def expand_needed (self):
		"""
		Check if running epxanding the source is needed.
		"""
		final = self.env.src_base + "-final.tex"
		if not exists(final):
			self.msg(3, _("the expanded file doesn't exist"))
			return 1
		# FIXME: the comparison below makes no sense, write a better one
		if getmtime(final) < getmtime(self.env.src_base + ".dvi"):
			self.msg(3, _("the expanded file is older than the DVI"))
			return 1
		self.msg(3, _("expansion is not needed"))
		return 0

	def expand_path (self, path):
		# self.out_stream.write("%%--- beginning of file %s\n" % path)
		file = open(path)

		# This is sort of a hack: we replace the 'seq' and 'hook' fields in
		# the environment with our own, in order to reuse the parsing routine.

		env = self.env
		saved_seq = env.seq ; env.seq = self.seq
		saved_hooks = env.hooks ; env.hooks = self.hooks
		self.env.do_process(file, path, seq=self.seq, dump=self.out_stream)
		env.hooks = saved_hooks
		env.seq = saved_seq

		file.close()
		# self.out_stream.write("%%--- end of file %s\n" % path)

	# The expansion hooks

	def x_remove (self, dict):
		pass

	def x_documentclass (self, dict):
		if not dict["arg"]: return
		file = self.env.conf.find_input (dict["arg"] + ".cls")
		if file:
			self.out_stream.write("\\makeatletter\n")
			self.expand_path(file)
			self.out_stream.write("\\makeatother\n")
		else:
			self.out_stream.write(dict["match"])

	def x_usepackage (self, dict):
		if not dict["arg"]: return
		remaining = []

		# Dump the contents of local packages.

		for name in string.split(dict["arg"], ","):
			file = self.env.conf.find_input(name + ".sty")
			if file and not exists(name + ".py"):
				self.out_stream.write("\\makeatletter\n")
				self.expand_path(file)
				self.out_stream.write("\\makeatother\n")
			else:
				remaining.append(name)

		# Rewrite a '\usepackage' for the remaining packages

		if remaining != []:
			self.out_stream.write("\\usepackage")
			if dict.has_key("opt") and dict["opt"]:
					self.out_stream.write("[%s]" % dict["opt"])
			self.out_stream.write("{%s}" % string.join(remaining, ","))

	def x_bibliographystyle (self, dict):
		if not dict["arg"]: return
		bbl = self.env.src_base + ".bbl"
		if exists(bbl):
			self.expand_path(bbl)
