# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
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
import rubber.cmdline

class Main (rubber.cmdline.Main):
	def short_help (self):
		msg(0, _("""\
usage: rubber-info [options] source
For more information, try `rubber-info --help'."""))

	def help (self):
		msg(0, _("""\
This is Rubber's information extractor version %s.
usage: rubber-info [options] source
available options:
  all options accepted by rubber(1)
actions:
  --boxes     report overfull and underfull boxes
  --check     report errors or warnings (default action)
  --deps      show the target file's dependencies
  --errors    show all errors that occured during compilation
  --help      display this help
  --refs      show the list of undefined references
  --rules     print the dependency rules including intermediate results
  --version   print the program's version and exit
  --warnings  show all LaTeX warnings\
""") % version)

	def parse_opts (self, cmdline):
		try:
			long =  [ "module=", "readopts=", "short", "verbose", "boxes",
				"check", "deps", "errors", "help", "refs", "rules", "version",
				"warnings" ]
			args = rubber.cmdline.Main.parse_opts(self, cmdline, long=long)
			opts, args = getopt(args, "", long)
			self.max_errors = -1
		except GetoptError, e:
			msg.error(e)
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
				msg.short = 1
			elif opt in ("-v", "--verbose"):
				msg.level = msg.level + 1
			elif opt == "--version":
				msg(0, version)
				sys.exit(0)
			else:
				if self.act:
					msg.error(_("You must specify only one action."))
					sys.exit(1)
				self.act = opt[2:]
		return args

	def main (self, cmdline):
		self.env = Environment()
		self.prologue = []
		self.epilogue = []

		self.act = None
		args = self.parse_opts(cmdline)
		if not self.act: self.act = "check"

		msg.log(_(
			"This is Rubber's information extractor version %s.") % version)

		if len(args) != 1:
			msg.error(_("You must specify one source file."))
			sys.exit(1)
		if exists(args[0] + ".tex"):
			src = args[0]
		elif exists(args[0]):
			src, ext = splitext(args[0])
		else:
			msg.error(_("I cannot find %s.") % args[0])
			sys.exit(1)

		if self.act == "deps":
			self.prepare(src)
			deps = {}
			for dep in self.env.main.sources.values():
				for file in dep.leaves():
					deps[file] = None
			print string.join(deps.keys())

		elif self.act == "rules":
			self.prepare(src)
			seen = {}
			next = [self.env.final]
			while len(next) > 0:
				node = next[0]
				next = next[1:]
				if seen.has_key(node):
					continue
				seen[node] = None
				if len(node.sources.keys()) == 0:
					continue
				print "\n%s:" % string.join(node.prods),
				print string.join(node.sources.keys())
				next.extend(node.sources.values())
		else:
			self.prepare(src)
			return self.info_log(src, self.act)

		return 0

	def prepare (self, src):
		"""
		Check for the source file and prepare it for processing.
		"""
		env = self.env

		if env.set_source(src):
			sys.exit(1)
		if env.make_source():
			sys.exit(1)

		for cmd in self.prologue:
			cmd = parse_line(cmd, {})
			env.main.command(cmd[0], cmd[1:], {'file': 'command line'})

		self.env.main.parse()

		for cmd in self.epilogue:
			cmd = parse_line(cmd, {})
			env.main.command(cmd[0], cmd[1:], {'file': 'command line'})

	def info_log (self, src, act):
		"""
		Check for a log file and extract information from it if it exists,
		accroding to the argument's value.
		"""
		logfile = src + ".log"
		if not exists(logfile):
			msg.error(_("I cannot find the log file."))
			return 1
		log = LogInfo(self.env.main)
		log.read(logfile)
		if act == "boxes":
			if not log.show_boxes():
				msg.info(_("There is no bad box."))
		elif act == "check":
			if log.show_errors(): return 0
			msg.info(_("There was no error."))
			if log.show_references(): return 0
			msg.info(_("There is no undefined reference."))
			if not log.show_warnings():	msg.info(_("There is no warning."))
			if not log.show_boxes(): msg.info(_("There is no bad box."))
		elif act == "errors":
			if not log.show_errors():
				msg.info(_("There was no error."))
		elif act == "refs":
			if not log.show_references():
				msg.info(_("There is no undefined reference."))
		elif act == "warnings":
			if not log.show_warnings():
				msg.info(_("There is no warning."))
		else:
			msg.error(_("\
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
			msg.error(_("*** interrupted"))
			return 2
