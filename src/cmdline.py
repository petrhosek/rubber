# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
This is the command line interface for Rubber.
"""

import sys
import os.path
import string
from getopt import *

from rubber import _, msg
from rubber import *
from rubber.version import *
from rubber.util import parse_line

class MoreErrors:
	"""
	This exception is raised when the maximum number of displayed errors is
	reached.
	"""
	pass

class Main (object):
	def __init__ (self):
		self.max_errors = 10
		msg.write = self.stderr_write

	def stderr_write (self, text, level=0):
		if level <= 0:
			self.max_errors = self.max_errors - 1
			if self.max_errors == -1:
				raise MoreErrors()
		sys.stderr.write(text + "\n")

	def short_help (self):
		"""
		Display a short description of the command line.
		"""
		msg(0, _("""\
usage: rubber [options] sources...
For more information, try `rubber --help'."""))

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		msg(0, _("""\
This is Rubber version %s.
usage: rubber [options] sources...
available options:
      --clean              remove produced files instead of compiling
  -c, --command=CMD        run the directive CMD before parsing (see man page)
  -e, --epilogue=CMD       run the directive CMD after parsing
  -f, --force              force at least one compilation
  -z, --gzip               compress the final document
  -h, --help               display this help
  -l, --landscape          change paper orientation (if relevant)
  -n, --maxerr=NUM         display at most NUM errors (default: 10)
  -m, --module=MOD[:OPTS]  use module MOD (with options OPTS)
  -o, --post=MOD[:OPTS]    postprocess with module MOD (with options OPTS)
  -d, --pdf                compile with pdftex (synonym for -m pdftex)
  -p, --ps                 process through dvips (synonym for -o dvips)
  -q, --quiet              suppress messages
  -r, --read=FILE          read additional directives from FILE
  -s, --short              display errors in a compact form
  -I, --texpath=DIR        add DIR to the search path for LaTeX
  -v, --verbose            increase verbosity
      --version            print version information and exit\
""") % version)

	def parse_opts (self, cmdline, short="", long=[]):
		try:
			opts, args = getopt(
				cmdline, "I:c:de:fhklm:n:o:pqr:svz" + short,
				["clean", "command=", "epilogue=", "force", "gzip", "help",
				 "keep", "landcape", "maxerr=", "module=", "post=", "pdf",
				 "ps", "quiet", "read=", "short", "texpath=", "verbose",
				 "version"] + long)
		except GetoptError, e:
			print e
			sys.exit(1)

		extra = []

		for (opt,arg) in opts:
			if opt == "--clean":
				self.clean = 1
			elif opt in ("-c", "--command"):
				self.prologue.append(arg)
			elif opt in ("-e", "--epilogue"):
				self.epilogue.append(arg)
			elif opt in ("-f", "--force"):
				self.force = 1
			elif opt in ("-z", "--gzip"):
				self.epilogue.append("module gz")
			elif opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt in ("-k", "--keep"):
				self.clean = 0
			elif opt in ("-l", "--landscape"):
				self.prologue.append("paper landscape")
			elif opt in ("-n", "--maxerr"):
				self.max_errors = int(arg)
			elif opt in ("-m", "--module"):
				self.prologue.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-o", "--post"):
				self.epilogue.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-d", "--pdf"):
				self.prologue.append("module pdftex")
			elif opt in ("-p", "--ps"):
				self.epilogue.append("module dvips")
			elif opt in ("-q", "--quiet"):
				msg.level = msg.level - 1
			elif opt in ("-r" ,"--read"):
				self.prologue.append("read " + arg)
			elif opt in ("-s", "--short"):
				msg.short = 1
			elif opt in ("-I", "--texpath"):
				self.prologue.append("path " + arg)
			elif opt in ("-v", "--verbose"):
				msg.level = msg.level + 1
			elif opt == "--version":
				print "Rubber version: " + version
				print "module path: " + moddir
				sys.exit(0)

			elif arg == "":
				extra.append(opt)
			else:
				extra.extend([arg, opt])

		return extra + args

	def main (self, cmdline):
		"""
		Run Rubber for the specified command line. This processes each
		specified source in order (for making or cleaning). If an error
		happens while making one of the documents, the whole process stops.
		The method returns the program's exit code.
		"""
		self.prologue = []
		self.epilogue = []
		self.clean = 0
		self.force = 0
		args = self.parse_opts(cmdline)
		msg.log(_("This is Rubber version %s.") % version)

		for src in args:
			env = Environment()

			# Check the source and prepare it for processing
	
			if env.set_source(src):
				sys.exit(1)

			for cmd in self.prologue:
				cmd = parse_line(cmd, {})
				env.command(cmd[0], cmd[1:], {'file': 'command line'})

			if self.clean:
				if not os.path.exists(env.source()):
					msg.warn(_("there is no LaTeX source"))
					continue

			env.make_source()
			env.parse()

			for cmd in self.epilogue:
				cmd = parse_line(cmd, {})
				env.command(cmd[0], cmd[1:], {'file': 'command line'})

			# Compile the document

			if self.clean:
				env.clean(1)
			else:
				if self.force:
					ret = env.make(1)
					if ret != 0:
						ret = env.final.make()
					else:
						# This is a hack for the call to show_errors() below
						# to work when compiling failed when using -f.
						env.final.failed_dep = env
				else:
					ret = env.final.make(self.force)

				if ret == 1:
					msg.info(_("nothing to be done for %s") % env.source())
				elif ret == 0:
					msg.info(_("There were errors compiling %s.")
						% env.source())
					try:
						env.final.failed().show_errors()
					except MoreErrors:
						msg.info(_("More errors."))
					return 1

		return 0

	def __call__ (self, cmdline):
		"""
		This method is a wrapper around the main method, showing a short help
		message when the command line is empty, and catching the keyboard
		interruption signal.
		"""
		if cmdline == []:
			self.short_help()
			return 1
		try:
			return self.main(cmdline)
		except KeyboardInterrupt:
			msg.error(_("*** interrupted"))
			return 2
