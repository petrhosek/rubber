# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
Support for the `graphics' package in Rubber.

This package is destined de become something rather large, to support standard
schemes for generating the figures that are supposed to be included, among
other features.

Another feature to include in the future concerns the parsing of the commands
that customize the operation of the package, such as \\DeclareGraphicsRule.

Currently, only dependency analysis is provided. The command parsing is
incomplete, because \\includegraphics can have a complex format.
"""

import os
from os.path import *
import string, re

import rubber
from rubber import _
from rubber import *
from rubber.util import *
import rubber.rules

# default suffixes for each device driver (taken from the .def files)

# For dvips and dvipdf we put the suffixes .bb instead of .gz because these
# are the files LaTeX actually looks for. The module `eps_gz' declares the
# gzipped files as dependencies for them and extracts the bounding box
# information.

drv_suffixes = {
	"dvipdf" : ["", ".eps", ".ps", ".eps.bb", ".ps.bb", ".eps.Z"],
	"dvipdfm" : ["", ".jpg", ".jpeg", ".pdf", ".png"],
	"dvips" : ["", ".eps", ".ps", ".eps.bb", ".ps.bb", ".eps.Z"],
	"dvipsone" : ["", ".eps", ".ps", ".pcx", ".bmp"],
	"dviwin" : ["", ".eps", ".ps", ".wmf", ".tif"],
	"emtex" : ["", ".eps", ".ps", ".pcx", ".bmp"],
	"pctex32" : ["", ".eps", ".ps", ".wmf", ".bmp"],
	"pctexhp" : ["", ".pcl"],
	"pctexps" : ["", ".eps", ".ps"],
	"pctexwin" : ["", ".eps", ".ps", ".wmf", ".bmp"],
	"pdftex" : ["", ".png", ".pdf", ".jpg", ".mps", ".tif"],
	"tcidvi" : [""],
	"textures" : ["", ".ps", ".eps", ".pict"],
	"truetex" : ["", ".eps", ".ps"],
	"vtex" : ["", ".gif", ".png", ".jpg", ".tif", ".bmp", ".tga", ".pcx",
	          ".eps", ".ps", ".mps", ".emf", ".wmf"]
}

# These regular expressions are used to parse path lists in \graphicspath and
# arguments in \DeclareGraphicsRule respectively.

re_gpath = re.compile("{(?P<prefix>[^{}]*)}")
re_grule = re.compile("{(?P<type>[^{}]*)}\\s*\
{(?P<read>[^{}]*)}\\s*{(?P<command>[^{}]*)}")

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		"""
		Initialize the module by defining the search path and the list of
		possible extensions from de compiler's name and the package's options.
		"""
		self.doc = doc
		self.env = doc.env
		doc.add_hook("includegraphics", self.includegraphics)
		doc.add_hook("graphicspath", self.graphicspath)
		doc.add_hook("DeclareGraphicsExtensions", self.declareExtensions)
		doc.add_hook("DeclareGraphicsRule", self.declareRule)
		doc.env.convert.add_rule("(.*)\\.(eps|pstex|pdf|pdftex)_t",
				"\\1.fig", 0, "fig2dev")

		self.prefixes = map(lambda x: join(x, ""), doc.env.path)
		self.files = []

		# I take dvips as the default, but it is not portable.
		if doc.conf.tex == "pdfTeX" and doc.prods[0][-4:] == ".pdf":
			self.suffixes = drv_suffixes["pdftex"]
		elif doc.conf.tex == "VTeX":
			self.suffixes = drv_suffixes["vtex"]
		else:
			self.suffixes = drv_suffixes["dvips"]

		if dict.has_key("opt") and dict["opt"]:
			self.opts = parse_keyval(dict["opt"])
		else:
			self.opts = {}

		for opt in self.opts.keys():
			if drv_suffixes.has_key(opt):
				self.suffixes = drv_suffixes[opt]

	#  supported macros

	def includegraphics (self, dict):
		"""
		This method is triggered by the \\includegraphics macro, it looks for
		the graphics file specified as argument and adds it either to the
		dependencies or to the list of graphics not found.
		"""
		name = dict["arg"]
		if not name:
			return
		suffixes = self.suffixes

		if dict["opt"]:
			opts = parse_keyval(dict["opt"])
			if opts.has_key("ext"):
				# no suffixes are tried when the extension is explicit
				suffixes = [""]
				if opts["ext"]:
					name = name + opts["ext"]

		if name.find("\\") >= 0 or name.find("#") >= 0:
			return

		d = rubber.rules.dep_file(name, suffixes, self.prefixes, self.env,
				dict["pos"])
		if d:
			msg.log(_("graphics `%s' found") % name)
			for file in d.prods:
				self.doc.sources[file] = d;
			self.files.append(d)
		else:
			msg.warn(_("graphics `%s' not found") % name, dict["pos"])

	def graphicspath (self, dict):
		"""
		This method is triggered by the \\graphicspath macro. The macro's
		argument is a list of prefixes that can be added to the file names
		(not only directory names).
		"""

		# This argument has the form {{foo/}{bar/}}, therefore it cannot be
		# parsed by the standard regular expression for control sequences
		# (because of the braces). Thus we parse the remains of the line
		# ourselves.

		if dict["arg"]:
			# The argument should be None...
			return

		line = dict["line"]
		if line[0] != "{":
			return
		line = line[1:]
		while line != "" and line[0] != "}":
			m = re_gpath.match(line)
			if m:
				self.prefixes.insert(0, m.group("prefix"))
				line = line[m.end():]
			else:
				# strange prefix, but we keep it anyway
				self.prefixes.insert(0, line[0])
				line = line[1:]

		dict["line"] = line

	def declareExtensions (self, dict):
		"""
		This method is triggered by the \\DeclareGraphicsExtensions macro. It
		registers new suffixes for graphics inclusion.
		"""
		if not dict["arg"]:
			return
		for suffix in dict["arg"].split(","):
			self.suffixes.insert(0, string.strip(suffix))

	def declareRule (self, dict):
		"""
		This method is triggered by the \\DeclareGraphicsRule macro. It
		declares a rule to include a given graphics file type.
		This implementation is preliminary, its correctness chould be checked.
		"""
		if not dict["arg"]:
			return
		m = re_grule.match(dict["line"])
		if not m:
			return
		dict["line"] = dict["line"][m.end():]
		read = m.group("read")
		if read in self.suffixes:
			return
		self.suffixes.insert(0, read)
		msg.log("*** FIXME ***  rule %s -> %s [%s]" % (
			string.strip(dict["arg"]), m.group("read"), m.group("type")))

	#  auxiliary method

	def find_input (self, name):
		"""
		Look for a source file with the given name and one of the registered
		suffixes, and return either the	complete path to the actual file or
		None if the file is not found.
		"""
		for prefix in self.prefixes:
			test = prefix + name
			if exists(test):
				return test
			for suffix in self.suffixes:
				if exists(test + suffix):
					return test + suffix
		return None

	#  module interface

	def pre_compile (self):
		"""
		Prepare the graphics before compilation. Currently, this only means
		printing warnings if some graphics are not found.
		"""
		for dep in self.files:
			dep.make()
		return 0

	def clean (self):
		"""
		Remove all graphics files that are produced by the transformation of
		some other file.
		"""
		for dep in self.files:
			dep.clean()

	def convert (self, source, target, env, loc={}):
		"""
		Return a dependency node (or None) for the conversion of the given
		source figure into the given target LaTeX source.
		"""
		return PSTDep(source, target, env, self, loc)
