# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
Support for the `graphics' package in Rubber.

This package is destined de become something rather large, to support standard
schemes for generating the figures that are supposed to be included, among
other features.

Another feature to include in the future concerns the parsing of the commands
that cusomize the operation of the package, such as \\DeclareGraphicsRule.

Currently, only dependency analysis is provided. The command parsing is
incomplete, because \\includegraphics can have a complex format.
"""

import os
from os.path import *
import string

def _ (txt): return txt

# default suffixes for each device driver (taken from the .def files)

drv_suffixes = {
	"dvipdf" : [".eps", ".ps", ".eps.gz", ".ps.gz", ".eps.Z"],
	"dvipdfm" : [".jpg", ".jpeg", ".pdf", ".png"],
	"dvips" : [".eps", ".ps", ".eps.gz", ".ps.gz", ".eps.Z"],
	"dvipsone" : [".eps", ".ps", ".pcx", ".bmp"],
	"dviwin" : [".eps", ".ps", ".wmf", ".tif"],
	"emtex" : [".eps", ".ps", ".pcx", ".bmp"],
	"pctex32" : [".eps", ".ps", ".wmf", ".bmp"],
	"pctexhp" : [".pcl"],
	"pctexps" : [".eps", ".ps"],
	"pctexwin" : [".eps", ".ps", ".wmf", ".bmp"],
	"pdftex" : [".png", ".pdf", ".jpg", ".mps", ".tif"],
	"tcidvi" : [""],
	"textures" : ["", ".ps", ".eps", ".pict"],
	"truetex" : [".eps", ".ps"],
	"vtex" : [".gif", ".png", ".jpg", ".tif", ".bmp", ".tga", ".pcx",
	          ".eps", ".ps", ".mps", ".emf", ".wmf"]
}

class Module:
	def __init__ (self, env, dict):
		"""
		Initialize the module by defining the search path and the list of
		possible extensions from de compiler's name and the package's options.
		"""
		self.env = env
		self.msg = env.message
		env.parser.add_hook("includegraphics", self.includegraphics)
		env.process.ext_building.append(self.build)

		self.path = env.config.path
		self.not_found = []

		# I take dvips as the default, but it is not portable.
		if env.config.tex == "pdfTeX":
			self.suffixes = drv_suffixes["pdftex"]
		else:
			self.suffixes = drv_suffixes["dvips"]
		if dict["opt"]:
			for opt in dict["opt"].split(","):
				if drv_suffixes.has_key(opt):
					self.suffixes = drv_suffixes[opt]

	def includegraphics (self, dict):
		"""
		This method is triggered by th \\includegraphics macro, it looks for
		the graphics file specified as argument and adds it either to the
		dependencies or to the list of graphics not found.
		"""
		name = dict["arg"]
		file = self.find_input(name)
		if file:
			self.env.process.depends.append(file)
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
			for suffix in self.suffixes:
				if exists(test + suffix):
					return test + suffix
		return None

	def build (self):
		"""
		Prepare the graphics before compilation. Currently, this only means
		printing warnings if some graphics are not found.
		"""
		if self.not_found == []:
			return 0
		self.msg(0, _("Warning: these graphics files were not found:"))
		self.msg(0, string.join(self.not_found, ", "))
		return 0
