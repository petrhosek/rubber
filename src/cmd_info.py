# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This is the command line interface for the information extractor.
"""

import sys
from getopt import *
import string
from os.path import *

from rubber import _
from rubber import *
from rubber.info import *
from rubber.version import *

class Main:
	def __init__ (self):
		self.msg = Message()

	def short_help (self):
		self.msg(0, _("""\
usage: rubber-info [options] source
For more information, try `rubber-info --help'."""))

	def help (self):
		self.msg(0, _("""\
This is Rubber's information extractor version %s.
usage: rubber-info [options] source
available options:
  -m / --module <mod>[:<options>] =
                   use a specific module (with the given options)
  -o / --readopts <file> =
                   read additional options from a file
  -s / --short   = display data in a compact form
  -v / --verbose = increase verbosity
actions:
  --boxes    = report overfull and underfull boxes
  --check    = report errors or warnings (default action)
  --deps     = show the target file's dependencies
  --errors   = show all errors that occured during compilation
  --help     = display this help
  --refs     = show the list of undefined references
  --version  = print the program's version and exit
  --warnings = show all LaTeX warnings\
""") % version)

	def parse_opts (self, cmdline):
		try:
			opts, args = getopt(
				cmdline, "hm:o:sv",
				["module=", "readopts=", "short", "verbose",
				 "boxes", "check", "deps", "errors", "help",
				 "refs", "version", "warnings"])
		except GetoptError, e:
			self.msg(0, e)
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
			elif opt in ("-s", "--short"):
				self.msg.short = 1
			elif opt in ("-v", "--verbose"):
				self.msg.level = self.msg.level + 1
			elif opt == "--version":
				self.msg(0, version)
				sys.exit(0)
			else:
				if self.act:
					self.msg(0, _("You must specify only one action."))
					sys.exit(1)
				self.act = opt[2:]
		return args

	def main (self, cmdline):
		self.env = Environment(self.msg)
		self.modules = []
		self.act = "check"
		args = self.parse_opts(cmdline)
		self.msg(1, _(
			"This is Rubber's information extractor version %s.") % version)

		if len(args) != 1:
			self.msg(0, _("You must specify one source file."))
			sys.exit(1)
		if exists(args[0] + ".tex"):
			src = args[0]
		elif exists(args[0]):
			src, ext = splitext(args[0])
		else:
			self.msg(0, _("I cannot find %s.") % args[0])
			sys.exit(1)

		if self.act == "deps":
			self.prepare(src)
			print "%s%s: %s" % (
				self.env.src_base,
				self.env.out_ext,
				string.join(self.env.depends.keys()))
		else:
			return self.info_log(src, self.act)

		return 0

	def prepare (self, src):
		"""
		Check for the source file and prepare it for processing.
		"""
		if self.env.set_source(src):
			sys.exit(1)
		if self.env.make_source():
			sys.exit(1)
		for mod in self.modules:
			colon = mod.find(":")
			if colon == -1:
				if self.env.modules.register(mod, { "arg": mod, "opt": None }):
					self.msg(
						0, _("module %s could not be registered") % mod)
			else:
				arg = { "arg": mod[:colon], "opt": mod[colon+1:] }
				mod = mod[0:colon]
				if self.env.modules.register(mod, arg):
					self.msg(
						0, _("module %s could not be registered") % mod)
		self.env.parse()

	def info_log (self, src, act):
		"""
		Check for a log file and extract information from it if it exists,
		accroding to the argument's value.
		"""
		logfile = src + ".log"
		if not exists(logfile):
			self.msg(0, _("I cannot find the log file."))
			return 1
		log = LogInfo(self.env)
		log.read(logfile)
		if act == "boxes":
			if not log.show_boxes():
				self.msg(0, _("There is no bad box."))
		elif act == "check":
			if log.show_errors(): return 0
			self.msg(0, _("There was no error."))
			if log.show_references(): return 0
			self.msg(0, _("There is no undefined reference."))
			if not log.show_warnings():	self.msg(0, _("There is no warning."))
			if not log.show_boxes(): self.msg(0, _("There is no bad box."))
		elif act == "errors":
			if not log.show_errors():
				self.msg(0, _("There was no error."))
		elif act == "refs":
			if not log.show_references():
				self.msg(0, _("There is no undefined reference."))
		elif act == "warnings":
			if not log.show_warnings():
				self.msg(0, _("There is no warning."))
		else:
			self.msg(0, _("\
I don't know the action `%s'. This should not happen.") % act)
			return 1
		return 0

	def __call__ (self, cmdline):
		if cmdline == []:
			self.short_help()
			return 1
		try:
			self.main(cmdline)
		except KeyboardInterrupt:
			self.msg(0, _("*** interrupted"))
			return 2
