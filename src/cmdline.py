# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This is the command line interface for Rubber.
"""

import sys
from getopt import *

from rubber import *
from rubber.version import *

def _ (txt) : return txt

class Main:
	def short_help (self):
		"""
		Display a short description of the command line.
		"""
		print _("""\
usage: rubber [options] source
For more information, try `rubber --help'.""")

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		print _("""\
This is Rubber version %s.
usage: rubber [options] source
available options:
       --clean   = remove produced files instead of compiling
  -h / --help    = display this help
  -m / --module <mod>[:<options>] =
                   use a specific module (with the given options)
  -d / --pdf     = produce PDF output instead of dvi (synonym for -m pdftex)
  -p / --ps      = produce a PostScript document (synonym for -m dvips)
  -q / --quiet   = suppress messages
  -o / --readopts <file> =
                   read additional options from a file
  -v / --verbose = increase verbosity
       --version = print version information and exit\
""" % version)

	def parse_opts (self, cmdline):
		try:
			opts, args = getopt(
				cmdline, "dhm:o:pqv",
				["clean", "pdf", "help", "module=", "readopts=", "ps",
				 "quiet", "verbose", "version"])
		except GetoptError, e:
			print e
			sys.exit(1)

		for (opt,arg) in opts:
			if opt == "--clean":
				self.clean = 1
			elif opt in ("-d", "--pdf"):
				self.modules.append("pdftex")
			elif opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt in ("-m", "--module"):
				self.modules.append(arg)
			elif opt in ("-o" ,"--readopts"):
				file = open(arg)
				opts2 = file.read().split()
				file.close()
				args = self.parse_opts(opts2) + args
			elif opt in ("-p", "--ps"):
				self.modules.append("dvips")
			elif opt in ("-q", "--quiet"):
				self.env.config.verb_level = -1
			elif opt in ("-v", "--verbose"):
				self.env.config.verb_level = self.env.config.verb_level + 1
			elif opt == "--version":
				print version
				sys.exit(0)

		return args

	def main (self, cmdline):
		"""
		Run Rubber for the specified command line.
		"""
		self.env = Environment()
		self.modules = []
		self.clean = 0
		args = self.parse_opts(cmdline)
		self.env.message(1, _("This is Rubber version %s.") % version)
		for src in args:
			self.prepare(src)
			if self.clean:
				self.env.clean()
			else:
				self.env.make()
		return 0

	def prepare (self, src):
		"""
		Check for the source file and prepare it for processing.
		"""
		if self.env.prepare(src):
			sys.exit(1)
		for mod in self.modules:
			colon = mod.find(":")
			if colon == -1:
				if self.env.modules.register(mod):
					self.env.message(
						0, _("module %s could not be registered") % mod)
			else:
				arg = { "arg" : mod[colon+1:] }
				mod = mod[0:colon]
				if self.env.modules.register(mod, arg):
					self.env.message(
						0, _("module %s could not be registered") % mod)

	def __call__ (self, cmdline):
		if cmdline == []:
			self.short_help()
			return 1
		self.main(cmdline)
