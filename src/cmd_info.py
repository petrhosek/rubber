# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This is the command line interface for the information extractor.
"""

import sys
from getopt import *
import string
from os.path import *

from rubber import *
from rubber.info import *
from rubber.version import *

def _ (txt) : return txt

class Main:
	def short_help (self):
		print _("""\
usage: rubber-info [options] source
For more information, try `rubber-info --help'.""")

	def help (self):
		print _("""\
This is Rubber's information extractor version %s.
usage: rubber-info [options] source
available options:
  -h / --help    = display this help
  -m / --module <mod>[:<options>] =
                   use a specific module (with the given options)
  -o / --readopts <file> =
                   read additional options from a file
  -v / --verbose = increase verbosity
       --version = print version information and exit
actions:
  --boxes  = report overfull and underfull boxes
  --deps   = show the target file's dependencies
  --errors = show all errors that occured during compilation\
""" % version)

	def parse_opts (self, cmdline):
		try:
			opts, args = getopt(
				cmdline, "hm:o:v",
				["help", "module=", "readopts=", "verbose", "version",
				 "boxes", "deps", "errors"])
		except GetoptError, e:
			print e
			sys.exit(1)

		for (opt,arg) in opts:
			if opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt in ("-m", "--module"):
				self.modules.append(arg)
			elif opt in ("-o" ,"--readopts"):
				file = open(arg)
				opts2 = file.read().split()
				file.close()
				args = self.parse_opts(opts2) + args
			elif opt in ("-v", "--verbose"):
				self.env.config.verb_level = self.env.config.verb_level + 1
			elif opt == "--version":
				print version
				sys.exit(0)
			else:
				self.act = opt[2:]
		return args

	def main (self, cmdline):
		self.env = Environment()
		self.modules = []
		self.act = None
		args = self.parse_opts(cmdline)
		self.env.message(1, _(
			"This is Rubber's information extractor version %s.") % version)

		if len(args) != 1:
			print _("You must specify one source file.")
			sys.exit(1)
		if exists(args[0] + ".tex"):
			src = args[0]
		elif exists(args[0]):
			src, ext = splitext(args[0])
		else:
			print _("I cannot find %s.") % args[0]
			sys.exit(1)

		if not self.act:
			print _("You must specify an action.")
			return 1

		elif self.act == "deps":
			self.prepare(src)
			print "%s%s: %s" % (
				self.env.process.src_pbase,
				self.env.process.out_ext,
				string.join(self.env.process.depends.keys()))
		else:
			return self.info_log(src, self.act)

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
		self.env.parse()

	def info_log (self, src, act):
		"""
		Check for a log file and extract information from it if it exists,
		accroding to the argument's value.
		"""
		logfile = src + ".log"
		if not exists(logfile):
			print _("I cannot find the log file.")
			return 1
		log = LogInfo(self.env)
		log.read(logfile)
		if act == "boxes":
			if not log.show_boxes():
				self.env.message(0, _("There is no bad box."))
		elif act == "errors":
			if not log.show_errors():
				self.env.message(0, _("There was no error."))
		else:
			print _("\
I don't know the action `%s'. This should not happen." % act)
			return 1
		return 0

	def __call__ (self, cmdline):
		if cmdline == []:
			self.short_help()
			return 1
		try:
			self.main(cmdline)
		except KeyboardInterrupt:
			print _("*** interrupted")
			return 2
