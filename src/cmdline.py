# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This is the command line interface for Rubber.
"""

import sys
import os.path
import string
from getopt import *

from rubber import _
from rubber import *
from rubber.version import *

class Main:
	def __init__ (self):
		"""
		Create the object used for message output.
		"""
		self.msg = Message()

	def short_help (self):
		"""
		Display a short description of the command line.
		"""
		self.msg (0, _("""\
usage: rubber [options] sources...
For more information, try `rubber --help'."""))

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		self.msg (0, _("""\
This is Rubber version %s.
usage: rubber [options] sources...
available options:
       --clean   = remove produced files instead of compiling
  -c / --command <cmd> = run the specified command
                   (see man page section "Directives" for details)
  -f / --force   = force at least one compilation
  -h / --help    = display this help
  -l / --landscape = change paper orientation (if relevant)
  -m / --module <mod>[:<options>] =
                   use a specific module (with the given options)
  -d / --pdf     = produce PDF output instead of DVI (synonym for -m pdftex)
  -p / --ps      = produce a PostScript document (synonym for -m dvips)
  -q / --quiet   = suppress messages
  -s / --short   = display errors in a compact form
  -r / --read <file> =
                   read additional directives from a file
  -v / --verbose = increase verbosity
       --version = print version information and exit\
""") % version)

	def parse_opts (self, cmdline):
		try:
			opts, args = getopt(
				cmdline, "c:dfhlm:pqr:sv",
				["clean", "command=", "force", "help", "landcape", "module=",
				 "pdf", "ps", "quiet", "read=", "short", "verbose", "version"])
		except GetoptError, e:
			print e
			sys.exit(1)

		for (opt,arg) in opts:
			if opt == "--clean":
				self.clean = 1
			elif opt in ("-c", "--command"):
				self.commands.append(arg)
			elif opt in ("-f", "--force"):
				self.force = 1
			elif opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt in ("-l", "--landscape"):
				self.commands.append("paper landscape")
			elif opt in ("-m", "--module"):
				self.commands.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-d", "--pdf"):
				self.commands.append("module pdftex")
			elif opt in ("-p", "--ps"):
				self.commands.append("module dvips")
			elif opt in ("-q", "--quiet"):
				self.msg.level = -1
			elif opt in ("-s", "--short"):
				self.msg.short = 1
			elif opt in ("-r" ,"--read"):
				self.commands.append("read " + arg)
			elif opt in ("-v", "--verbose"):
				self.msg.level = self.msg.level + 1
			elif opt == "--version":
				print version
				sys.exit(0)

		return args

	def main (self, cmdline):
		"""
		Run Rubber for the specified command line. This processes each
		specified source in order (for making or cleaning). If an error
		happens while making one of the documents, the whole process stops.
		The method returns the program's exit code.
		"""
		self.env = Environment(self.msg)
		env = self.env
		self.commands = []
		self.clean = 0
		self.force = 0
		args = self.parse_opts(cmdline)
		self.msg(2, _("This is Rubber version %s.") % version)
		first = 1
		for src in args:
			if not first:
				env.restart()
			self.prepare(src)
			first = 0
			if self.clean:
				env.clean()
			else:
				error = env.make(self.force)
				if not error and not env.something_done:
					self.msg(0, _("nothing to be done for %s") % env.source())
				elif error == 1:
					if not self.msg.short:
						self.msg(-1, _("There were errors compiling %s.")
							% env.source())
					env.log.show_errors()
				if error:
					return error
		return 0

	def prepare (self, src):
		"""
		Check for the source file and prepare it for processing. This executes
		the directives from the command line before parsing the sources.
		"""
		env = self.env
		if env.set_source(src):
			sys.exit(1)
		for cmd in self.commands:
			cmd = string.split(cmd, maxsplit = 1)
			if len(cmd) == 1:
				cmd.append("")
			env.command(cmd[0], cmd[1])
		if self.clean and not os.path.exists(env.source()):
			self.msg(1, _("there is no LaTeX source"))
		else:
			env.make_source()
			env.parse()

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
			self.msg(0, _("*** interrupted"))
			return 2
