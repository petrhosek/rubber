# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
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
import string

import rubber.util
import rubber.graphics

def _ (txt): return txt

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
	"pdftex" : ["", ".pdf", ".png", ".jpg", ".mps", ".tif"],
	"tcidvi" : [""],
	"textures" : ["", ".ps", ".eps", ".pict"],
	"truetex" : ["", ".eps", ".ps"],
	"vtex" : ["", ".gif", ".png", ".jpg", ".tif", ".bmp", ".tga", ".pcx",
	          ".eps", ".ps", ".mps", ".emf", ".wmf"]
}

class Module:
	def __init__ (self, env, dict):
		"""
		Initialize the module by defining the search path and the list of
		possible extensions from de compiler's name and the package's options.
		"""
		self.env = env
		self.msg = env.msg
		env.add_hook("includegraphics", self.includegraphics)
		env.ext_building.append(self.build)
		env.cleaning_process.append(self.clean)

		self.path = env.conf.path
		self.files = []
		self.not_found = []

		# I take dvips as the default, but it is not portable.
		if env.conf.tex == "pdfTeX":
			self.suffixes = drv_suffixes["pdftex"]
		else:
			self.suffixes = drv_suffixes["dvips"]

		if dict["opt"]:
			self.opts = rubber.util.parse_keyval(dict["opt"])
		else:
			self.opts = {}

		for opt in self.opts.keys():
			if drv_suffixes.has_key(opt):
				self.suffixes = drv_suffixes[opt]

	def includegraphics (self, dict):
		"""
		This method is triggered by th \\includegraphics macro, it looks for
		the graphics file specified as argument and adds it either to the
		dependencies or to the list of graphics not found.
		"""
		name = dict["arg"]
		suffixes = self.suffixes

		if dict["opt"]:
			opts = rubber.util.parse_keyval(dict["opt"])
			if opts.has_key("ext"):
				# no suffixes are tried when the extension is explicit
				suffixes = [""]
				if opts["ext"]:
					name = name + opts["ext"]

		d = rubber.graphics.dep_file(name, suffixes, self.path, self.env)
		if d:
			self.msg(1, _("graphics %s found") % name)
			for file in d.prods:
				self.env.depends[file] = d;
			self.files.append(d)
		else:
			self.not_found.append(name)

	def find_input (self, name):
		"""
		Look for a source file with the given name and one of the registered
		suffixes, and return either the	complete path to the actual file or
		None if the file is not found.
		"""
		for path in self.path:
			test = join(path, name)
			if exists(test):
				return test
			for suffix in self.suffixes:
				if exists(test + suffix):
					return test + suffix
		return None

	def build (self):
		"""
		Prepare the graphics before compilation. Currently, this only means
		printing warnings if some graphics are not found.
		"""
		for dep in self.files:
			dep.make()
		if self.not_found == []:
			return 0
		self.msg(0, _("Warning: these graphics files were not found:"))
		self.msg(0, string.join(self.not_found, ", "))
		return 0

	def clean (self):
		"""
		Remove all graphics files that are produced by the transformation of
		some other file.
		"""
		for dep in self.files:
			dep.clean()
